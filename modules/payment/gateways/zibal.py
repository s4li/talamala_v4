"""
Zibal Gateway
==============
REST/JSON. Sandbox: merchant="zibal" → auto-succeed.
"""

import httpx
import logging
from typing import Dict, Any

from config.settings import ZIBAL_MERCHANT
from modules.payment.gateways import (
    BaseGateway, GatewayPaymentRequest, GatewayCreateResult,
    GatewayVerifyResult, register_gateway,
)

logger = logging.getLogger("talamala.gateway.zibal")

ZIBAL_REQUEST_URL = "https://gateway.zibal.ir/v1/request"
ZIBAL_VERIFY_URL = "https://gateway.zibal.ir/v1/verify"
ZIBAL_START_URL = "https://gateway.zibal.ir/start/{trackId}"


class ZibalGateway(BaseGateway):
    name = "zibal"
    label = "زیبال"

    def create_payment(self, req: GatewayPaymentRequest) -> GatewayCreateResult:
        try:
            resp = httpx.post(ZIBAL_REQUEST_URL, json={
                "merchant": ZIBAL_MERCHANT,
                "amount": req.amount_irr,
                "callbackUrl": req.callback_url,
                "description": req.description,
                "orderId": req.order_ref,
            }, timeout=15)
            data = resp.json()
            logger.info(f"Zibal create [{req.order_ref}]: {data}")

            if data.get("result") == 100:
                track_id = str(data["trackId"])
                return GatewayCreateResult(
                    success=True,
                    redirect_url=ZIBAL_START_URL.format(trackId=track_id),
                    track_id=track_id,
                )
            else:
                msg = data.get("message", f"کد خطا: {data.get('result')}")
                return GatewayCreateResult(success=False, error_message=f"خطا در درگاه: {msg}")

        except httpx.TimeoutException:
            return GatewayCreateResult(success=False, error_message="درگاه پاسخ نداد. دوباره تلاش کنید.")
        except Exception as e:
            logger.error(f"Zibal create failed: {e}")
            return GatewayCreateResult(success=False, error_message=f"خطا در اتصال به درگاه: {e}")

    def verify_payment(self, params: Dict[str, Any]) -> GatewayVerifyResult:
        track_id = params.get("trackId", "")
        try:
            resp = httpx.post(ZIBAL_VERIFY_URL, json={
                "merchant": ZIBAL_MERCHANT,
                "trackId": int(track_id),
            }, timeout=15)
            data = resp.json()
            logger.info(f"Zibal verify [{track_id}]: {data}")

            if data.get("result") == 100:
                ref_number = str(data.get("refNumber", track_id))
                return GatewayVerifyResult(success=True, ref_number=ref_number)
            else:
                msg = data.get("message", f"کد: {data.get('result')}")
                return GatewayVerifyResult(success=False, error_message=f"تراکنش ناموفق — {msg}")

        except Exception as e:
            logger.error(f"Zibal verify failed: {e}")
            return GatewayVerifyResult(success=False, error_message=f"خطا در تأیید: {e}")


register_gateway(ZibalGateway())
