"""
TalaMala v4 - SMS Provider (Kavenegar)
========================================
Handles OTP and notification SMS sending.
"""

import logging
import requests
import urllib3

from config.settings import SMS_API_KEY

# Disable SSL warnings (for Iran's network restrictions)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("talamala.sms")

if not SMS_API_KEY:
    logger.warning("⚠️ SMS_API_KEY not set in .env - SMS sending disabled")


class SmsSender:
    """Kavenegar SMS service wrapper."""

    def send_otp_lookup(
        self,
        receptor: str,
        token: str,
        token2: str = None,
        token3: str = None,
        template_name: str = "OTP",
    ) -> bool:
        """
        Send OTP via Kavenegar Verify/Lookup API.

        Args:
            receptor: Mobile number
            token: First template variable (e.g., user name)
            token2: Second template variable (e.g., OTP code)
            token3: Third template variable (optional)
            template_name: Kavenegar template name
        """
        # Always print OTP to console for debugging
        print(f"\n{'='*40}")
        print(f"[OTP] CODE (DEBUG): {token2}")
        print(f"[OTP] To: {receptor}")
        print(f"{'='*40}\n")

        if not SMS_API_KEY:
            logger.warning("SMS skipped: no API key configured")
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
                logger.info(f"✅ SMS sent to {receptor}")
                return True
            else:
                logger.error(f"❌ SMS API Error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error("❌ SMS Timeout: Kavenegar connection too slow")
            return False
        except Exception as e:
            logger.error(f"❌ SMS Connection Failed: {e}")
            return False


# Singleton instance
sms_sender = SmsSender()
