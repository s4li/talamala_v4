"""
Hedging / Position Management Service
========================================
Tracks company's net metal exposure across all sales channels.
Uses atomic DB-level updates on MetalPosition to prevent race conditions.
All position changes are recorded in PositionLedger (immutable audit trail).
"""

import logging
import threading
import uuid
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func, desc

from modules.hedging.models import MetalPosition, PositionLedger, PositionDirection

logger = logging.getLogger("talamala.hedging")

# Default shop closed message for alerts
_DEFAULT_THRESHOLD_GOLD_MG = 50000      # 50 grams
_DEFAULT_THRESHOLD_SILVER_MG = 500000   # 500 grams
_DEFAULT_COOLDOWN_MINUTES = 60


class HedgingService:

    # ==========================================
    # Core: Atomic ledger writer
    # ==========================================

    def _record(
        self,
        db: Session,
        metal_type: str,
        direction: str,
        amount_mg: int,
        source_type: str,
        source_id: str = "",
        description: str = "",
        metal_price_per_gram: int = None,
        recorded_by: int = None,
        idempotency_key: str = None,
    ) -> Optional[PositionLedger]:
        """
        Atomic position update + ledger write.

        Uses DB-level atomic update on MetalPosition.balance_mg to prevent
        race conditions under concurrent load:
            UPDATE metal_positions SET balance_mg = balance_mg + :delta WHERE ...

        Returns PositionLedger entry, or None if idempotency key already exists.
        Caller must commit.
        """
        # ADJUST carries signed delta (can be negative for downward corrections)
        if direction == PositionDirection.ADJUST:
            if amount_mg == 0:
                return None
        elif amount_mg <= 0:
            return None

        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = f"{source_type}:{source_id}:{metal_type}:{uuid.uuid4().hex[:8]}"

        # Check for duplicate
        existing = db.query(PositionLedger).filter(
            PositionLedger.idempotency_key == idempotency_key
        ).first()
        if existing:
            logger.debug(f"Hedging: idempotency key already exists: {idempotency_key}")
            return None

        # Calculate delta (signed)
        if direction in (PositionDirection.OUT,):
            delta_mg = -amount_mg  # Position decreases
        elif direction in (PositionDirection.IN, PositionDirection.HEDGE):
            # HEDGE direction is determined by caller (buy=IN, sell=OUT)
            delta_mg = amount_mg   # Position increases
        elif direction == PositionDirection.ADJUST:
            delta_mg = amount_mg   # Signed value from caller
        else:
            delta_mg = amount_mg

        # Ensure MetalPosition row exists
        pos = db.query(MetalPosition).filter(
            MetalPosition.metal_type == metal_type
        ).with_for_update().first()

        if not pos:
            pos = MetalPosition(metal_type=metal_type, balance_mg=0)
            db.add(pos)
            db.flush()
            # Re-acquire with lock
            pos = db.query(MetalPosition).filter(
                MetalPosition.metal_type == metal_type
            ).with_for_update().first()

        # Atomic DB-level update (no Python read-modify-write)
        db.query(MetalPosition).filter(
            MetalPosition.metal_type == metal_type
        ).update(
            {MetalPosition.balance_mg: MetalPosition.balance_mg + delta_mg},
            synchronize_session="fetch",
        )

        # Read back new balance for ledger entry
        db.flush()
        db.refresh(pos)
        new_balance = pos.balance_mg

        # Write immutable ledger entry
        entry = PositionLedger(
            metal_type=metal_type,
            direction=direction,
            amount_mg=abs(amount_mg),
            balance_after_mg=new_balance,
            source_type=source_type,
            source_id=source_id or "",
            description=description or "",
            metal_price_per_gram=metal_price_per_gram,
            recorded_by=recorded_by,
            idempotency_key=idempotency_key,
        )
        db.add(entry)
        db.flush()

        # Threshold alert (non-blocking daemon thread)
        self._maybe_send_alert(metal_type, new_balance)

        return entry

    # ==========================================
    # Public: Called from integration hooks
    # ==========================================

    def record_out(
        self, db: Session, metal_type: str, amount_mg: int,
        source_type: str, source_id: str = "", description: str = "",
    ) -> Optional[PositionLedger]:
        """Record an OUT event (we gave metal to customer). Position decreases."""
        idem_key = f"{source_type}:{source_id}:{metal_type}"
        return self._record(
            db, metal_type, PositionDirection.OUT, amount_mg,
            source_type=source_type, source_id=source_id,
            description=description, idempotency_key=idem_key,
        )

    def record_in(
        self, db: Session, metal_type: str, amount_mg: int,
        source_type: str, source_id: str = "", description: str = "",
    ) -> Optional[PositionLedger]:
        """Record an IN event (we received metal from customer). Position increases."""
        idem_key = f"{source_type}:{source_id}:{metal_type}"
        return self._record(
            db, metal_type, PositionDirection.IN, amount_mg,
            source_type=source_type, source_id=source_id,
            description=description, idempotency_key=idem_key,
        )

    # ==========================================
    # Admin: Hedge recording + adjustment
    # ==========================================

    def record_hedge(
        self, db: Session, metal_type: str, hedge_direction: str,
        amount_mg: int, metal_price_per_gram: int = None,
        description: str = "", admin_id: int = None,
    ) -> PositionLedger:
        """
        Admin records a physical market trade.
        hedge_direction: 'buy' (we bought from market → IN) or 'sell' (we sold → OUT)
        """
        if hedge_direction == "buy":
            direction = PositionDirection.IN
        else:
            direction = PositionDirection.OUT

        return self._record(
            db, metal_type, direction, amount_mg,
            source_type="hedge", source_id=f"hedge:{uuid.uuid4().hex[:8]}",
            description=description,
            metal_price_per_gram=metal_price_per_gram,
            recorded_by=admin_id,
        )

    def set_initial_balance(
        self, db: Session, metal_type: str, balance_mg: int,
        admin_id: int = None, description: str = "",
    ) -> Optional[PositionLedger]:
        """
        Admin sets initial position or makes a manual correction.
        balance_mg is the DESIRED final balance (not a delta).
        We compute the delta from current balance.
        """
        pos = db.query(MetalPosition).filter(
            MetalPosition.metal_type == metal_type
        ).first()

        current = pos.balance_mg if pos else 0
        delta = balance_mg - current

        if delta == 0:
            return None  # No change needed

        # For ADJUST, amount_mg carries the signed delta
        return self._record(
            db, metal_type, PositionDirection.ADJUST, delta,
            source_type="admin_adjust",
            source_id=f"adjust:{uuid.uuid4().hex[:8]}",
            description=description or f"Manual adjustment: {current/1000:.3f}g -> {balance_mg/1000:.3f}g",
            recorded_by=admin_id,
        )

    # ==========================================
    # Queries
    # ==========================================

    def get_position(self, db: Session, metal_type: str) -> dict:
        """Get current position for a metal type."""
        pos = db.query(MetalPosition).filter(
            MetalPosition.metal_type == metal_type
        ).first()

        if not pos:
            return {
                "balance_mg": 0, "balance_grams": 0.0,
                "status": "hedged", "status_label": "پوشش کامل",
                "status_color": "success", "metal_label": metal_type,
                "updated_at": None,
            }

        return {
            "balance_mg": pos.balance_mg,
            "balance_grams": pos.balance_grams,
            "status": pos.status,
            "status_label": pos.status_label,
            "status_color": pos.status_color,
            "metal_label": pos.metal_label,
            "updated_at": pos.updated_at,
        }

    def get_all_positions(self, db: Session) -> dict:
        """Get positions for all metal types."""
        return {
            "gold": self.get_position(db, "gold"),
            "silver": self.get_position(db, "silver"),
        }

    def get_ledger(
        self, db: Session, metal_type: str = None,
        source_type: str = None, direction: str = None,
        page: int = 1, per_page: int = 30,
    ) -> Tuple[List[PositionLedger], int]:
        """Paginated ledger with optional filters."""
        q = db.query(PositionLedger)

        if metal_type:
            q = q.filter(PositionLedger.metal_type == metal_type)
        if source_type:
            q = q.filter(PositionLedger.source_type == source_type)
        if direction:
            q = q.filter(PositionLedger.direction == direction)

        total = q.count()
        entries = q.order_by(desc(PositionLedger.created_at)).offset(
            (page - 1) * per_page
        ).limit(per_page).all()

        return entries, total

    def get_summary(self, db: Session, metal_type: str = None) -> dict:
        """Summary stats for dashboard."""
        from common.helpers import now_utc
        from datetime import timedelta

        now = now_utc()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        q = db.query(PositionLedger)
        if metal_type:
            q = q.filter(PositionLedger.metal_type == metal_type)

        # Total OUT (sold to customers)
        total_out = q.filter(
            PositionLedger.direction == PositionDirection.OUT,
        ).with_entities(sa_func.coalesce(sa_func.sum(PositionLedger.amount_mg), 0)).scalar()

        # Total IN (received from customers)
        total_in = q.filter(
            PositionLedger.direction == PositionDirection.IN,
        ).with_entities(sa_func.coalesce(sa_func.sum(PositionLedger.amount_mg), 0)).scalar()

        # Total hedged
        total_hedged = q.filter(
            PositionLedger.direction == PositionDirection.HEDGE,
        ).with_entities(sa_func.coalesce(sa_func.sum(PositionLedger.amount_mg), 0)).scalar()

        # Entries today
        entries_today = q.filter(
            PositionLedger.created_at >= today_start,
        ).count()

        # Entries this week
        entries_week = q.filter(
            PositionLedger.created_at >= week_start,
        ).count()

        return {
            "total_out_mg": total_out,
            "total_in_mg": total_in,
            "total_hedged_mg": total_hedged,
            "total_out_grams": float(total_out) / 1000.0,
            "total_in_grams": float(total_in) / 1000.0,
            "total_hedged_grams": float(total_hedged) / 1000.0,
            "entries_today": entries_today,
            "entries_week": entries_week,
        }

    def get_chart_data(self, db: Session, metal_type: str, days: int = 30) -> list:
        """Get balance history for chart (last N days)."""
        from common.helpers import now_utc
        from datetime import timedelta

        cutoff = now_utc() - timedelta(days=days)
        entries = db.query(PositionLedger).filter(
            PositionLedger.metal_type == metal_type,
            PositionLedger.created_at >= cutoff,
        ).order_by(PositionLedger.created_at).all()

        return [
            {
                "date": e.created_at.strftime("%Y-%m-%d %H:%M"),
                "balance_grams": e.balance_after_mg / 1000.0,
            }
            for e in entries
        ]

    # ==========================================
    # Threshold alert (non-blocking)
    # ==========================================

    def _maybe_send_alert(self, metal_type: str, balance_mg: int):
        """
        Check threshold and send admin alert if exceeded.
        Runs SMS dispatch in a daemon thread to never block the caller's request.
        Uses its own DB session to avoid interfering with the caller's transaction.
        """
        threading.Thread(
            target=self._send_alert_thread,
            args=(metal_type, balance_mg),
            daemon=True,
        ).start()

    def _send_alert_thread(self, metal_type: str, balance_mg: int):
        """Background thread: check threshold and send notification."""
        try:
            from config.database import SessionLocal
            db = SessionLocal()
            try:
                self._check_and_send_alert(db, metal_type, balance_mg)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Hedging alert error: {e}")

    def _check_and_send_alert(self, db: Session, metal_type: str, balance_mg: int):
        """Check threshold config and send alert if needed (runs in background thread)."""
        from common.templating import get_setting_from_db
        from common.helpers import now_utc
        from modules.admin.models import SystemSetting

        # Check if alerts are enabled
        if get_setting_from_db(db, "hedge_alert_enabled", "true") != "true":
            return

        # Check threshold
        threshold_key = f"hedge_threshold_{metal_type}_mg"
        defaults = {"gold": _DEFAULT_THRESHOLD_GOLD_MG, "silver": _DEFAULT_THRESHOLD_SILVER_MG}
        threshold = int(get_setting_from_db(db, threshold_key, str(defaults.get(metal_type, 50000))))

        if abs(balance_mg) <= threshold:
            return  # Within acceptable range

        # Check cooldown
        cooldown_minutes = int(get_setting_from_db(db, "hedge_alert_cooldown_minutes",
                                                    str(_DEFAULT_COOLDOWN_MINUTES)))
        last_alert_key = f"hedge_last_alert_{metal_type}"
        last_alert = db.query(SystemSetting).filter(SystemSetting.key == last_alert_key).first()

        if last_alert and last_alert.value:
            from datetime import datetime, timezone
            try:
                last_ts = datetime.fromisoformat(last_alert.value)
                elapsed = (now_utc() - last_ts).total_seconds()
                if elapsed < cooldown_minutes * 60:
                    return  # Still in cooldown
            except (ValueError, TypeError):
                pass

        # Send alert to all admins
        from modules.user.models import User
        admins = db.query(User).filter(
            User.is_admin == True, User.is_active == True
        ).all()

        metal_label = {"gold": "طلا", "silver": "نقره"}.get(metal_type, metal_type)
        grams = abs(balance_mg) / 1000.0
        status = "کمبود" if balance_mg < 0 else "مازاد"

        alert_title = f"هشدار پوشش ریسک {metal_label}"
        alert_body = f"{status} {grams:,.1f} گرم {metal_label} — نیاز به اقدام فوری"
        sms_text = f"طلاملا: {status} {grams:,.1f}g {metal_label} — /admin/hedging"

        from modules.notification.service import notification_service
        from modules.notification.models import NotificationType

        for admin in admins:
            try:
                notification_service.send(
                    db, admin.id,
                    notification_type=NotificationType.SYSTEM,
                    title=alert_title,
                    body=alert_body,
                    link="/admin/hedging",
                    sms_text=sms_text,
                    admin_alert_text=alert_body,
                )
            except Exception as e:
                logger.error(f"Failed to send hedging alert to admin #{admin.id}: {e}")

        # Update cooldown timestamp
        now_str = now_utc().isoformat()
        if last_alert:
            last_alert.value = now_str
        else:
            db.add(SystemSetting(key=last_alert_key, value=now_str))


# Singleton
hedging_service = HedgingService()
