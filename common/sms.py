"""
TalaMala v4 - SMS Provider (Kavenegar + sms.ir)
=================================================
Handles OTP and notification SMS sending.
Supports multiple providers with admin-panel switching.
Default provider: sms.ir
"""

import logging
import requests
import urllib3

from config.settings import (
    SMS_API_KEY,
    SMSIR_API_KEY,
    SMSIR_LINE_NUMBER,
    SMSIR_TEMPLATE_ID,
)

# Disable SSL warnings (for Iran's network restrictions)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("talamala.sms")

if not SMSIR_API_KEY and not SMS_API_KEY:
    logger.warning("No SMS API keys configured - SMS sending disabled")


def _get_active_provider() -> str:
    """Read active SMS provider from DB setting. Default: 'smsir'."""
    try:
        from config.database import SessionLocal
        from modules.admin.models import SystemSetting
        session = SessionLocal()
        try:
            setting = session.query(SystemSetting).filter(
                SystemSetting.key == "sms_provider"
            ).first()
            return setting.value if setting else "smsir"
        finally:
            session.close()
    except Exception:
        return "smsir"


class SmsSender:
    """Multi-provider SMS service (Kavenegar + sms.ir)."""

    def send_otp_lookup(
        self,
        receptor: str,
        token: str,
        token2: str = None,
        token3: str = None,
        template_name: str = "OTP",
    ) -> bool:
        """
        Send OTP via active SMS provider.

        Args:
            receptor: Mobile number
            token: First template variable (e.g., user name)
            token2: Second template variable (e.g., OTP code)
            token3: Third template variable (optional)
            template_name: Kavenegar template name (ignored for sms.ir)
        """
        # Always print OTP to console for debugging
        print(f"\n{'='*40}")
        print(f"[OTP] CODE (DEBUG): {token2}")
        print(f"[OTP] To: {receptor}")
        print(f"{'='*40}\n")

        provider = _get_active_provider()
        logger.info(f"SMS provider: {provider}")

        if provider == "kavenegar":
            return self._send_kavenegar(receptor, token, token2, token3, template_name)
        else:
            return self._send_smsir(receptor, token, token2, token3)

    # ------------------------------------------
    # Kavenegar
    # ------------------------------------------

    def _send_kavenegar(self, receptor, token, token2, token3, template_name) -> bool:
        """Send via Kavenegar Verify/Lookup API."""
        if not SMS_API_KEY:
            logger.warning("SMS skipped: no Kavenegar API key configured")
            return False

        try:
            url = f"https://api.kavenegar.com/v1/{SMS_API_KEY}/verify/lookup.json"
            params = {
                "receptor": receptor,
                "token": token,
                "template": template_name,
            }
            if token2:
                params["token2"] = token2
            if token3:
                params["token3"] = token3

            response = requests.get(url, params=params, timeout=5, verify=False)

            if response.status_code == 200:
                logger.info(f"SMS sent via Kavenegar to {receptor}")
                return True
            else:
                logger.error(f"Kavenegar Error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error("Kavenegar Timeout")
            return False
        except Exception as e:
            logger.error(f"Kavenegar Failed: {e}")
            return False

    # ------------------------------------------
    # sms.ir
    # ------------------------------------------

    def _send_smsir(self, receptor, token, token2, token3) -> bool:
        """Send via sms.ir API. Uses verify (template) if configured, else bulk."""
        if not SMSIR_API_KEY:
            logger.warning("SMS skipped: no sms.ir API key configured")
            return False

        if SMSIR_TEMPLATE_ID:
            return self._send_smsir_verify(receptor, token, token2, token3)
        else:
            return self._send_smsir_bulk(receptor, token, token2)

    def _send_smsir_verify(self, receptor, token, token2, token3) -> bool:
        """Send via sms.ir Verify (template) API."""
        try:
            url = "https://api.sms.ir/v1/send/verify"
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/plain",
                "X-API-KEY": SMSIR_API_KEY,
            }
            parameters = [{"name": "NAME", "value": str(token)}]
            if token2:
                parameters.append({"name": "CODE", "value": str(token2)})
            if token3:
                parameters.append({"name": "TOKEN3", "value": str(token3)})

            payload = {
                "mobile": receptor,
                "templateId": int(SMSIR_TEMPLATE_ID),
                "parameters": parameters,
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            data = response.json()

            if response.status_code == 200 and data.get("status") == 1:
                logger.info(f"SMS sent via sms.ir verify to {receptor}")
                return True
            else:
                logger.error(f"sms.ir verify Error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error("sms.ir Timeout")
            return False
        except Exception as e:
            logger.error(f"sms.ir Failed: {e}")
            return False

    def _send_smsir_bulk(self, receptor, token, token2) -> bool:
        """Send via sms.ir Bulk (plain text) API - fallback when no template."""
        try:
            otp_code = token2 or ""
            name = token or "کاربر"
            message = f"طلاملا\n{name} عزیز\nکد تایید شما: {otp_code}"

            url = "https://api.sms.ir/v1/send/bulk"
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/plain",
                "X-API-KEY": SMSIR_API_KEY,
            }
            payload = {
                "lineNumber": int(SMSIR_LINE_NUMBER),
                "messageText": message,
                "mobiles": [receptor],
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            data = response.json()

            if response.status_code == 200 and data.get("status") == 1:
                logger.info(f"SMS sent via sms.ir bulk to {receptor}")
                return True
            else:
                logger.error(f"sms.ir bulk Error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error("sms.ir Timeout")
            return False
        except Exception as e:
            logger.error(f"sms.ir Failed: {e}")
            return False

    # ------------------------------------------
    # Credit check (for admin diagnostics)
    # ------------------------------------------

    def check_smsir_credit(self) -> dict:
        """Check sms.ir account credit. Returns {'success': bool, 'credit': int}."""
        if not SMSIR_API_KEY:
            return {"success": False, "error": "API key not configured"}
        try:
            url = "https://api.sms.ir/v1/credit"
            headers = {"Accept": "text/plain", "X-API-KEY": SMSIR_API_KEY}
            response = requests.get(url, headers=headers, timeout=5)
            data = response.json()
            if response.status_code == 200 and data.get("status") == 1:
                return {"success": True, "credit": data.get("data", 0)}
            return {"success": False, "error": data.get("message", "Unknown error")}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
sms_sender = SmsSender()
