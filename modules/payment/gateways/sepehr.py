"""
Sepehr Gateway (Saman / Mabna)
================================
REST/JSON. TerminalId-based token → redirect → Advice verify.
"""

import requests
import logging
from typing import Dict, Any

from config.settings import SEPEHR_TERMINAL_ID
from modules.payment.gateways import (
    BaseGateway, GatewayPaymentRequest, GatewayCreateResult,
    GatewayVerifyResult, register_gateway,
)

logger = logging.getLogger("talamala.gateway.sepehr")

SEPEHR_TOKEN_URL = "https://sepehr.shaparak.ir/Rest/V1/PeymentApi/GetToken"
SEPEHR_PAY_URL = "https://sepehr.shaparak.ir/Payment/Pay"
SEPEHR_ADVICE_URL = "https://sepehr.shaparak.ir/Rest/V1/PeymentApi/Advice"


class SepehrGateway(BaseGateway):
    name = "sepehr"
    label = "سپهر"

    def create_payment(self, req: GatewayPaymentRequest) -> GatewayCreateResult:
        data = {
            "Amount": req.amount_irr,
            "callbackURL": req.callback_url,
            "invoiceID": req.order_ref,
            "terminalID": SEPEHR_TERMINAL_ID,
            "payload": req.description or "",
        }
        try:
            resp = requests.post(SEPEHR_TOKEN_URL, json=data, timeout=15)
            result = resp.json()
            logger.info(f"Sepehr token [{req.order_ref}]: {result}")

            if result.get("Status") == 0:
                token = result.get("Accesstoken")
                if not token:
                    return GatewayCreateResult(success=False, error_message="توکن پرداخت از سپهر دریافت نشد")

                redirect_url = f"{SEPEHR_PAY_URL}?token={token}&terminalId={SEPEHR_TERMINAL_ID}"
                return GatewayCreateResult(
                    success=True,
                    redirect_url=redirect_url,
                    track_id=str(token),
                )
            else:
                return GatewayCreateResult(
                    success=False,
                    error_message=f"خطای سپهر (کد {result.get('Status')})",
                )

        except requests.Timeout:
            return GatewayCreateResult(success=False, error_message="درگاه سپهر پاسخ نداد.")
        except requests.RequestException as e:
            logger.error(f"Sepehr connection error: {e}")
            return GatewayCreateResult(success=False, error_message="خطای ارتباط با درگاه سپهر")

    def verify_payment(self, params: Dict[str, Any]) -> GatewayVerifyResult:
        """
        Verify via Advice endpoint.
        params must include: digitalreceipt, expected_amount
        """
        digital_receipt = params.get("digitalreceipt", "")
        expected_amount = params.get("expected_amount", 0)

        data = {
            "digitalreceipt": str(digital_receipt),
            "Tid": SEPEHR_TERMINAL_ID,
        }
        try:
            resp = requests.post(SEPEHR_ADVICE_URL, json=data, timeout=15)
            result = resp.json()
            logger.info(f"Sepehr advice [{digital_receipt[:20]}...]: {result}")

            status = str(result.get("Status", "")).lower()
            return_amount = result.get("ReturnId")

            if status in ("ok", "duplicate") and int(return_amount) == int(expected_amount):
                return GatewayVerifyResult(success=True, ref_number=str(return_amount))
            else:
                logger.warning(
                    f"Sepehr verify failed: Status={status}, ReturnId={return_amount}, Expected={expected_amount}"
                )
                return GatewayVerifyResult(success=False, error_message=f"تراکنش سپهر ناموفق (وضعیت: {status})")

        except Exception as e:
            logger.error(f"Sepehr verify failed: {e}")
            return GatewayVerifyResult(success=False, error_message=f"خطا در تأیید سپهر: {e}")


register_gateway(SepehrGateway())
