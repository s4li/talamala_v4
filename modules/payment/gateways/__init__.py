"""
Payment Gateway Abstraction
=============================
Each gateway implements create_payment() and verify_payment().
Registry pattern for gateway lookup by name.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("talamala.gateway")


@dataclass
class GatewayPaymentRequest:
    """Input for creating a payment."""
    amount_irr: int
    callback_url: str
    description: str
    order_ref: str          # order_id or topup_id as string
    mobile: str = ""        # optional customer mobile


@dataclass
class GatewayCreateResult:
    """Result of create_payment()."""
    success: bool
    redirect_url: Optional[str] = None
    track_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class GatewayVerifyResult:
    """Result of verify_payment()."""
    success: bool
    ref_number: Optional[str] = None
    error_message: Optional[str] = None


class BaseGateway:
    """Abstract gateway interface."""
    name: str = ""
    label: str = ""  # Persian display name

    def create_payment(self, req: GatewayPaymentRequest) -> GatewayCreateResult:
        raise NotImplementedError

    def verify_payment(self, params: Dict[str, Any]) -> GatewayVerifyResult:
        raise NotImplementedError


# ── Registry ──

_GATEWAYS: Dict[str, BaseGateway] = {}


def register_gateway(gw: BaseGateway):
    _GATEWAYS[gw.name] = gw


def get_gateway(name: str) -> Optional[BaseGateway]:
    return _GATEWAYS.get(name)


def get_all_gateway_names() -> List[str]:
    return list(_GATEWAYS.keys())
