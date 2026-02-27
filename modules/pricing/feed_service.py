"""
Pricing Module - External Price Feed Service
===============================================
Fetches live asset prices from external APIs (e.g. goldis.ir).
"""

import logging
from typing import Dict

import httpx

logger = logging.getLogger("talamala.pricing.feed")

GOLDIS_PRICES_URL = "https://products.goldis.ir/api/v3/prices"
GOLDIS_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
GOLDIS_TIMEOUT = 5  # seconds


def _fetch_goldis_prices() -> Dict[str, int]:
    """
    Fetch all prices from goldis.ir v3 API in one HTTP call.

    Returns:
        dict mapping code → buy_price (int, rial per gram)
        e.g. {"GOLD18": 202756851, "SILVER": 5508540}

    Raises:
        ValueError: If response is invalid.
        httpx.HTTPError: On network/HTTP errors.
    """
    resp = httpx.get(
        GOLDIS_PRICES_URL,
        headers={"User-Agent": GOLDIS_USER_AGENT},
        timeout=GOLDIS_TIMEOUT,
    )
    resp.raise_for_status()

    data = resp.json()
    if not data.get("success"):
        raise ValueError(f"Goldis API returned success=false: {data}")
    if not isinstance(data.get("data"), list):
        raise ValueError(f"Goldis API missing 'data' list: {data}")

    return {item["code"]: int(item["buy_price"]) for item in data["data"]}


def fetch_gold_price_goldis() -> int:
    """
    Fetch 18K gold price from goldis.ir API.

    Returns:
        Price per gram in Rials (int).

    Raises:
        ValueError: If response is invalid or price is non-positive.
        httpx.HTTPError: On network/HTTP errors.
    """
    prices = _fetch_goldis_prices()
    price = prices.get("GOLD18")
    if not price or price <= 0:
        raise ValueError(f"Invalid gold price from goldis: {price}")

    logger.info(f"Fetched gold 18K price from goldis: {price:,} rial")
    return price


def fetch_silver_price_goldis() -> int:
    """
    Fetch silver price from goldis.ir API.

    Returns:
        Price per gram in Rials (int).

    Raises:
        ValueError: If response is invalid or price is non-positive.
        httpx.HTTPError: On network/HTTP errors.
    """
    prices = _fetch_goldis_prices()
    price = prices.get("SILVER")
    if not price or price <= 0:
        raise ValueError(f"Invalid silver price from goldis: {price}")

    logger.info(f"Fetched silver price from goldis: {price:,} rial")
    return price
