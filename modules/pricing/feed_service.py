"""
Pricing Module - External Price Feed Service
===============================================
Fetches live asset prices from external APIs (e.g. goldis.ir).
"""

import logging

import httpx

logger = logging.getLogger("talamala.pricing.feed")

GOLDIS_GOLD18K_URL = "https://goldis.ir/price/api/v1/price/assets/gold18k/final-prices"
GOLDIS_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
GOLDIS_TIMEOUT = 5  # seconds


def fetch_gold_price_goldis() -> int:
    """
    Fetch 18K gold price from goldis.ir API.

    Returns:
        Price per gram in Rials (int).

    Raises:
        ValueError: If response is invalid or price is non-positive.
        httpx.HTTPError: On network/HTTP errors.
    """
    resp = httpx.get(
        GOLDIS_GOLD18K_URL,
        headers={"User-Agent": GOLDIS_USER_AGENT},
        timeout=GOLDIS_TIMEOUT,
    )
    resp.raise_for_status()

    data = resp.json()
    if not data.get("success"):
        raise ValueError(f"Goldis API returned success=false: {data}")
    if "data" not in data:
        raise ValueError(f"Goldis API missing 'data' key: {data}")

    price = int(data["data"]["final_buy_price"])
    if price <= 0:
        raise ValueError(f"Invalid price from goldis: {price}")

    logger.info(f"Fetched gold 18K price from goldis: {price:,} rial")
    return price
