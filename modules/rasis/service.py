"""
Rasis POS Integration Service
================================
Syncs gold bar inventory and pricing to Rasis POS devices at dealer locations.

Rasis API docs: DocumentWebApi2.4.88.pdf
Base URL (test): https://mttestapi.rasisclub.ir
Auth: GET /api/Token → UniqCode header on all requests (short-lived tokens)
"""

import logging
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from config.settings import RASIS_API_URL, RASIS_USERNAME, RASIS_PASSWORD
from common.templating import get_setting_from_db

logger = logging.getLogger("talamala.rasis")

RASIS_UNION_ID = 22  # لوازم کادویی و کالای لوکس (5950)
RASIS_BRANCH_CATEGORY_ID = 9  # Fixed category for branch registration
RASIS_TIMEOUT = 20  # seconds


def _is_enabled(db: Session) -> bool:
    """Check if Rasis POS sync is enabled in admin settings."""
    return get_setting_from_db(db, "rasis_pos_enabled", "false") == "true"


def _has_credentials() -> bool:
    """Check if Rasis API credentials are configured."""
    return bool(RASIS_API_URL and RASIS_USERNAME and RASIS_PASSWORD)


class RasisService:
    """Rasis POS API integration — sync bars to dealer POS devices."""

    # ------------------------------------------
    # Auth
    # ------------------------------------------

    def _get_token(self) -> Optional[tuple]:
        """
        GET /api/Token?userName=X&password=Y → (UserId, TokenValue).
        Returns None on failure. Tokens are short-lived so we get fresh ones.
        """
        if not _has_credentials():
            logger.warning("Rasis: credentials not configured")
            return None

        try:
            resp = httpx.get(
                f"{RASIS_API_URL}/api/Token",
                params={"userName": RASIS_USERNAME, "password": RASIS_PASSWORD},
                timeout=RASIS_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.error(f"Rasis token: HTTP {resp.status_code}")
                return None

            data = resp.json()
            if not data.get("IsSuccess"):
                logger.error(f"Rasis token failed: {data.get('Messages')}")
                return None

            token_data = data.get("Data", {})
            user_id = token_data.get("UserId", 0)
            token_value = token_data.get("TokenValue", "")
            if not token_value or user_id <= 0:
                logger.error("Rasis token: empty token or invalid user_id")
                return None

            return (user_id, token_value)

        except httpx.TimeoutException:
            logger.error("Rasis token: timeout")
            return None
        except Exception as e:
            logger.error(f"Rasis token error: {e}")
            return None

    def _headers(self, token: str) -> dict:
        """Build headers with UniqCode for authenticated requests."""
        return {
            "UniqCode": token,
            "Content-Type": "application/json",
        }

    # ------------------------------------------
    # Branch Management
    # ------------------------------------------

    def register_branch(self, db: Session, dealer) -> Optional[int]:
        """
        Register dealer as a Rasis branch (شعبه).
        Uses POST /api/Branches (org) then POST /api/Branch (branch).
        Returns the assigned sharepoint ID or None on failure.

        NOTE: If Sharepoint is already set, Rasis updates instead of creating.
        """
        if not _is_enabled(db) or not _has_credentials():
            return None

        auth = self._get_token()
        if not auth:
            return None
        user_id, token = auth

        province_name = dealer.province.name if dealer.province else "ایران"
        city_name = dealer.city.name if dealer.city else "تهران"
        phone = dealer.landline_phone or dealer.mobile or ""
        mobile = dealer.mobile or ""

        # Step 1: Register مجموعه (Branches — org level)
        branches_body = {
            "Name": dealer.full_name,
            "Owner": dealer.full_name,
            "IsBranch": True,
            "Status": True,
            "IsClubMember": False,
            "WebServiceUrl": RASIS_API_URL,
            "BranchTerminals": [],
            "UserId": user_id,
            "BranchCategoryId": RASIS_BRANCH_CATEGORY_ID,
            "CountryName": "Iran",
            "ProvinceName": province_name,
            "CityName": city_name,
            "PhoneNumber": mobile[:12] if mobile else "",
            "Phone": phone[:15] if phone else "",
        }

        # If dealer already has a sharepoint, include it (Rasis will update)
        if dealer.rasis_sharepoint:
            branches_body["Sharepoint"] = dealer.rasis_sharepoint

        try:
            resp = httpx.post(
                f"{RASIS_API_URL}/api/Branches",
                json=branches_body,
                headers=self._headers(token),
                timeout=RASIS_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.error(f"Rasis Branches: HTTP {resp.status_code} - {resp.text[:200]}")
                return None

            data = resp.json()
            if not data.get("IsSuccess"):
                logger.error(f"Rasis Branches failed: {data.get('Messages')}")
                return None

        except Exception as e:
            logger.error(f"Rasis Branches error: {e}")
            return None

        # Step 2: Register شعبه (Branch — gets Sharepoint back)
        # Need fresh token (short-lived)
        auth2 = self._get_token()
        if not auth2:
            return None
        user_id2, token2 = auth2

        branch_body = {
            "Name": dealer.full_name,
            "Owner": dealer.full_name,
            "Status": True,
            "Color": "#00A3C7",
            "UserId": user_id2,
            "BrandName": "طلاملا",
            "MainBranch": "طلاملا",
            "BranchManager": dealer.full_name,
            "IsBranch": True,
            "IsClubMember": False,
            "WebServiceUrl": RASIS_API_URL,
            "BranchTerminals": [],
            "BranchCategoryId": RASIS_BRANCH_CATEGORY_ID,
            "CountryName": "Iran",
            "ProvinceName": province_name,
            "CityName": city_name,
            "PhoneNumber": mobile[:12] if mobile else "",
            "Phone": phone[:15] if phone else "",
        }

        if dealer.rasis_sharepoint:
            branch_body["SharepointBranches"] = dealer.rasis_sharepoint
            branch_body["Sharepoint"] = dealer.rasis_sharepoint

        try:
            resp2 = httpx.post(
                f"{RASIS_API_URL}/api/Branch",
                json=branch_body,
                headers=self._headers(token2),
                timeout=RASIS_TIMEOUT,
            )
            if resp2.status_code != 200:
                logger.error(f"Rasis Branch: HTTP {resp2.status_code} - {resp2.text[:200]}")
                return None

            data2 = resp2.json()
            if not data2.get("IsSuccess", True):
                logger.error(f"Rasis Branch failed: {data2.get('Messages')}")
                return None

            # Extract sharepoint from response
            # The Branch API returns Sharepoint in the response body
            sharepoint = data2.get("Sharepoint")
            if not sharepoint and isinstance(data2.get("Data"), dict):
                sharepoint = data2["Data"].get("Sharepoint")

            if sharepoint:
                dealer.rasis_sharepoint = int(sharepoint)
                db.flush()
                logger.info(f"Rasis: dealer {dealer.id} registered, sharepoint={sharepoint}")
                return int(sharepoint)
            else:
                # Try FindBranchID to get the sharepoint
                logger.warning("Rasis Branch: no sharepoint in response, trying FindBranchID")
                return None

        except Exception as e:
            logger.error(f"Rasis Branch error: {e}")
            return None

    # ------------------------------------------
    # Commodity CRUD
    # ------------------------------------------

    def add_bar_to_pos(self, db: Session, bar, dealer) -> bool:
        """
        POST /api/CommodityCustomer/Add — add bar as commodity on dealer's POS.

        Mapping:
        - Cbrc = bar.serial_code (barcode)
        - Cnme = bar.serial_code (commodity name = serial on POS)
        - Tgrp = bar.product.name (group = product type name)
        - Camtby/Camtsl = calculated bar price
        - Barcodes = [bar.serial_code]
        - Sharepoint = dealer.rasis_sharepoint
        - UnionID = 22
        """
        if not _is_enabled(db) or not _has_credentials():
            return False

        if not dealer.rasis_sharepoint:
            logger.warning(f"Rasis add_bar: dealer {dealer.id} has no sharepoint")
            return False

        if not bar.product:
            logger.warning(f"Rasis add_bar: bar {bar.serial_code} has no product")
            return False

        # Calculate price
        price = self._calculate_bar_price(db, bar)
        if not price:
            return False

        auth = self._get_token()
        if not auth:
            return False
        user_id, token = auth

        product_name = bar.product.name if bar.product else "شمش طلا"

        body = {
            "Sharepoint": dealer.rasis_sharepoint,
            "Tuit": "Q",  # واحد: عدد
            "Cbrc": bar.serial_code,
            "Cnme": bar.serial_code,
            "Camtby": float(price),
            "Camtsl": float(price),
            "UserId": user_id,
            "Tgrp": product_name,
            "CstD": True,
            "ValueAddedTaxPercentage": 0,
            "UnionID": RASIS_UNION_ID,
            "Barcodes": [bar.serial_code],
        }

        try:
            resp = httpx.post(
                f"{RASIS_API_URL}/api/CommodityCustomer/Add",
                json=body,
                headers=self._headers(token),
                timeout=RASIS_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.error(f"Rasis add_bar: HTTP {resp.status_code} for {bar.serial_code}")
                return False

            data = resp.json()
            if data.get("IsSuccess"):
                logger.info(f"Rasis: added bar {bar.serial_code} to dealer {dealer.id} POS")
                return True
            else:
                logger.error(f"Rasis add_bar failed: {data.get('Messages')} for {bar.serial_code}")
                return False

        except Exception as e:
            logger.error(f"Rasis add_bar error: {e}")
            return False

    def remove_bar_from_pos(self, db: Session, bar, dealer) -> bool:
        """
        DELETE /api/CommodityCustomer/Delete — remove bar from POS when sold.
        """
        if not _is_enabled(db) or not _has_credentials():
            return False

        if not dealer.rasis_sharepoint:
            return False

        auth = self._get_token()
        if not auth:
            return False
        user_id, token = auth

        try:
            resp = httpx.delete(
                f"{RASIS_API_URL}/api/CommodityCustomer/Delete",
                params={
                    "cbrc": bar.serial_code,
                    "sharepoint": dealer.rasis_sharepoint,
                    "userId": user_id,
                    "unionId": RASIS_UNION_ID,
                },
                headers=self._headers(token),
                timeout=RASIS_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.error(f"Rasis remove_bar: HTTP {resp.status_code} for {bar.serial_code}")
                return False

            data = resp.json()
            if data.get("IsSuccess"):
                logger.info(f"Rasis: removed bar {bar.serial_code} from dealer {dealer.id} POS")
                return True
            else:
                logger.error(f"Rasis remove_bar failed: {data.get('Messages')}")
                return False

        except Exception as e:
            logger.error(f"Rasis remove_bar error: {e}")
            return False

    def update_bar_price_on_pos(self, db: Session, bar, dealer, price: int) -> bool:
        """
        POST /api/CommodityCustomer/UpdatePrice — update price for a single bar.
        """
        if not dealer.rasis_sharepoint:
            return False

        auth = self._get_token()
        if not auth:
            return False
        user_id, token = auth

        body = {
            "Sharepoint": dealer.rasis_sharepoint,
            "Cbrc": bar.serial_code,
            "Camtby": float(price),
            "Camtsl": float(price),
            "UserId": user_id,
            "CstD": True,
            "ValueAddedTaxPercentage": 0,
            "UnionID": RASIS_UNION_ID,
            "Barcodes": [bar.serial_code],
        }

        try:
            resp = httpx.post(
                f"{RASIS_API_URL}/api/CommodityCustomer/UpdatePrice",
                json=body,
                headers=self._headers(token),
                timeout=RASIS_TIMEOUT,
            )
            if resp.status_code != 200:
                return False

            data = resp.json()
            return data.get("IsSuccess", False)

        except Exception as e:
            logger.error(f"Rasis update_price error: {e}")
            return False

    # ------------------------------------------
    # Batch Operations
    # ------------------------------------------

    def update_prices_on_pos(self, db: Session) -> int:
        """
        Update prices for all ASSIGNED bars at dealers with rasis_sharepoint.
        Called by background scheduler when gold price changes.
        Returns count of updated bars.
        """
        from modules.inventory.models import Bar, BarStatus
        from modules.user.models import User

        if not _is_enabled(db) or not _has_credentials():
            return 0

        # Get all ASSIGNED bars at dealers who have rasis_sharepoint
        bars = (
            db.query(Bar)
            .join(User, Bar.dealer_id == User.id)
            .filter(
                Bar.status == BarStatus.ASSIGNED,
                Bar.product_id.isnot(None),
                User.rasis_sharepoint.isnot(None),
                User.is_dealer == True,
                User.is_active == True,
            )
            .all()
        )

        if not bars:
            return 0

        updated = 0
        # Group bars by dealer for efficiency (one token per dealer batch)
        dealer_bars = {}
        for bar in bars:
            did = bar.dealer_id
            if did not in dealer_bars:
                dealer_bars[did] = []
            dealer_bars[did].append(bar)

        for dealer_id, dealer_bar_list in dealer_bars.items():
            dealer = db.query(User).get(dealer_id)
            if not dealer or not dealer.rasis_sharepoint:
                continue

            for bar in dealer_bar_list:
                price = self._calculate_bar_price(db, bar)
                if price and self.update_bar_price_on_pos(db, bar, dealer, price):
                    updated += 1

        return updated

    def sync_dealer_inventory(self, db: Session, dealer) -> dict:
        """
        Full sync: ensure all ASSIGNED bars at this dealer are on POS.
        Returns {"added": N, "errors": N}.
        """
        from modules.inventory.models import Bar, BarStatus

        if not _is_enabled(db) or not _has_credentials():
            return {"added": 0, "errors": 0, "skipped": True}

        # Register branch if no sharepoint yet
        if not dealer.rasis_sharepoint:
            sp = self.register_branch(db, dealer)
            if not sp:
                return {"added": 0, "errors": 0, "error": "Failed to register Rasis branch"}

        bars = (
            db.query(Bar)
            .filter(
                Bar.dealer_id == dealer.id,
                Bar.status == BarStatus.ASSIGNED,
                Bar.product_id.isnot(None),
            )
            .all()
        )

        added = 0
        errors = 0
        for bar in bars:
            if self.add_bar_to_pos(db, bar, dealer):
                added += 1
            else:
                errors += 1

        logger.info(f"Rasis sync dealer {dealer.id}: added={added}, errors={errors}, total={len(bars)}")
        return {"added": added, "errors": errors, "total": len(bars)}

    # ------------------------------------------
    # Helpers
    # ------------------------------------------

    def _calculate_bar_price(self, db: Session, bar) -> Optional[int]:
        """Calculate the current price for a bar using the pricing calculator."""
        from modules.pricing.calculator import calculate_bar_price
        from modules.pricing.models import Asset

        if not bar.product:
            return None

        from modules.pricing.service import get_product_pricing
        p_price, p_bp, _ = get_product_pricing(db, bar.product)
        if not p_price:
            return None

        tax_str = get_setting_from_db(db, "tax_percent", "10")
        tax_pct = float(tax_str) if tax_str else 10.0

        result = calculate_bar_price(
            weight=bar.product.weight,
            purity=bar.product.purity,
            wage_percent=float(bar.product.wage or 0),
            base_metal_price=p_price,
            tax_percent=tax_pct,
            base_purity=p_bp,
        )

        return result.get("total") if not result.get("error") else None


rasis_service = RasisService()
