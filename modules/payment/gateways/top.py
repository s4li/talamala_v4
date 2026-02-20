"""
Top Gateway (PNA / Top.ir)
============================
REST/JSON with Basic Auth. CreateOrder → redirect → ConfirmPurchase.
"""

import base64
import datetime
import requests
import logging
from typing import Dict, Any

from config.settings import TOP_USERNAME, TOP_PASSWORD
from modules.payment.gateways import (
    BaseGateway, GatewayPaymentRequest, GatewayCreateResult,
    GatewayVerifyResult, register_gateway,
)

logger = logging.getLogger("talamala.gateway.top")

TOP_BASE_URL = "https://pay.top.ir/api/WPG"


class TopGateway(BaseGateway):
    name = "top"
    label = "تاپ"

    def _auth_headers(self) -> dict:
        combine = base64.b64encode(f"{TOP_USERNAME}:{TOP_PASSWORD}".encode()).decode()
        return {"Authorization": f"Basic {combine}"}

    def create_payment(self, req: GatewayPaymentRequest) -> GatewayCreateResult:
        url = f"{TOP_BASE_URL}/CreateOrder"
        order_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        payload = {
            "MerchantOrderId": req.order_ref,
            "MerchantOrderDate": order_date,
            "AdditionalData": req.description or "",
            "Amount": req.amount_irr,
            "CallBackUrl": req.callback_url,
            "ReceptShowTime": 0,
            "walletCode": TOP_USERNAME,
            "MobileNumber": req.mobile or "",
        }

        try:
            resp = requests.post(url, headers=self._auth_headers(), json=payload, timeout=15)
            result = resp.json()
            logger.info(f"Top create [{req.order_ref}]: {result}")

            if result.get("status") == 0:
                data = result.get("data", {})
                token = data.get("token")
                if not token:
                    return GatewayCreateResult(success=False, error_message="توکن پرداخت از تاپ دریافت نشد")

                payment_url = data["serviceURL"]
                return GatewayCreateResult(
                    success=True,
                    redirect_url=payment_url,
                    track_id=str(token),
                )
            else:
                msg = result.get("message", "خطای ناشناخته")
                return GatewayCreateResult(
                    success=False,
                    error_message=f"خطای تاپ: {msg} (کد {result.get('status')})",
                )

        except requests.Timeout:
            return GatewayCreateResult(success=False, error_message="درگاه تاپ پاسخ نداد.")
        except requests.RequestException as e:
            logger.error(f"Top connection error: {e}")
            return GatewayCreateResult(success=False, error_message="خطای ارتباط با درگاه تاپ")

    def verify_payment(self, params: Dict[str, Any]) -> GatewayVerifyResult:
        """
        Verify via ConfirmPurchase.
        params must include: token, MerchantOrderId
        """
        url = f"{TOP_BASE_URL}/ConfirmPurchase"
        transaction_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        payload = {
            "token": params.get("token", ""),
            "MerchantOrderId": params.get("MerchantOrderId", ""),
            "transactionDateTime": transaction_date,
            "additionalData": "",
        }

        try:
            resp = requests.post(url, headers=self._auth_headers(), json=payload, timeout=15)
            result = resp.json()
            logger.info(f"Top confirm [{params.get('MerchantOrderId')}]: {result}")

            if result.get("status") == 0:
                data = result.get("data", {})
                rrn = str(data.get("rrn", "N/A"))
                return GatewayVerifyResult(success=True, ref_number=rrn)
            else:
                msg = result.get("message", "ناموفق")
                return GatewayVerifyResult(
                    success=False,
                    error_message=f"تراکنش تاپ ناموفق: {msg} (کد {result.get('status')})",
                )

        except Exception as e:
            logger.error(f"Top verify failed: {e}")
            return GatewayVerifyResult(success=False, error_message=f"خطا در تأیید تاپ: {e}")


register_gateway(TopGateway())
