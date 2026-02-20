"""
Parsian Gateway (PEC)
======================
SOAP/WSDL via zeep. SalePaymentRequest → redirect → ConfirmPayment.
"""

import logging
from typing import Dict, Any

from config.settings import PARSIAN_PIN
from modules.payment.gateways import (
    BaseGateway, GatewayPaymentRequest, GatewayCreateResult,
    GatewayVerifyResult, register_gateway,
)

logger = logging.getLogger("talamala.gateway.parsian")

PARSIAN_SALE_WSDL = "https://pec.shaparak.ir/NewIPGServices/Sale/SaleService.asmx?wsdl"
PARSIAN_CONFIRM_WSDL = "https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService.asmx?wsdl"
PARSIAN_REDIRECT_URL = "https://pec.shaparak.ir/NewIPG/?token={token}"

# Lazy-loaded SOAP clients (zeep Client init is slow)
_sale_client = None
_confirm_client = None


def _get_sale_client():
    global _sale_client
    if _sale_client is None:
        from zeep import Client
        _sale_client = Client(PARSIAN_SALE_WSDL)
    return _sale_client


def _get_confirm_client():
    global _confirm_client
    if _confirm_client is None:
        from zeep import Client
        _confirm_client = Client(PARSIAN_CONFIRM_WSDL)
    return _confirm_client


class ParsianGateway(BaseGateway):
    name = "parsian"
    label = "پارسیان"

    def create_payment(self, req: GatewayPaymentRequest) -> GatewayCreateResult:
        try:
            client = _get_sale_client()
            request_data = {
                "LoginAccount": PARSIAN_PIN,
                "OrderId": int(req.order_ref),
                "Amount": req.amount_irr,
                "CallBackUrl": req.callback_url,
                "AdditionalData": req.description or "",
                "Originator": req.mobile or "",
            }

            result = client.service.SalePaymentRequest(requestData=request_data)
            logger.info(f"Parsian sale [{req.order_ref}]: Status={result['Status']}, Token={result['Token']}")

            status = result["Status"]
            token = result["Token"]
            message = result.get("Message", "")

            if status != 0 or token <= 0:
                return GatewayCreateResult(
                    success=False,
                    error_message=f"خطای پارسیان: {message} (کد {status})",
                )

            redirect_url = PARSIAN_REDIRECT_URL.format(token=token)
            return GatewayCreateResult(
                success=True,
                redirect_url=redirect_url,
                track_id=str(token),
            )

        except Exception as e:
            logger.error(f"Parsian create failed: {e}")
            return GatewayCreateResult(success=False, error_message=f"خطا در اتصال به پارسیان: {e}")

    def verify_payment(self, params: Dict[str, Any]) -> GatewayVerifyResult:
        """
        Verify via ConfirmPayment.
        params must include: Token, status, RRN
        """
        token_raw = params.get("Token", "")
        status_raw = params.get("status", -1)
        rrn_raw = params.get("RRN", "")

        try:
            status = int(status_raw) if status_raw is not None else -1
            rrn = int(rrn_raw) if rrn_raw else 0
            token = int(token_raw) if token_raw else 0
        except (ValueError, TypeError):
            return GatewayVerifyResult(success=False, error_message="پارامترهای بازگشت نامعتبر")

        try:
            client = _get_confirm_client()
            request_data = {
                "LoginAccount": PARSIAN_PIN,
                "Token": token,
            }

            confirm_result = client.service.ConfirmPayment(requestData=request_data)
            confirm_status = confirm_result["Status"]
            logger.info(f"Parsian confirm [token={token}]: Status={confirm_status}")

            if confirm_status == 0:
                return GatewayVerifyResult(success=True, ref_number=str(rrn or token))
            else:
                return GatewayVerifyResult(
                    success=False,
                    error_message=f"تأیید پارسیان ناموفق (کد: {confirm_status})",
                )

        except Exception as e:
            logger.error(f"Parsian confirm failed: {e}")
            return GatewayVerifyResult(success=False, error_message=f"خطا در تأیید پارسیان: {e}")


register_gateway(ParsianGateway())
