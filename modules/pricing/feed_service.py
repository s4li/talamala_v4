"""
Pricing Module - External Price Feed Service
===============================================
Fetches live asset prices from external APIs.

Primary source: sawiss.com (WordPress "zioto" pricing plugin)
Fallback source: goldis.ir v3 API

The sawiss endpoint requires a WordPress nonce that expires (12-24h). The nonce is
scraped from the homepage, cached, and re-fetched automatically on 400/403.
"""

import json
import logging
import re
import threading
from typing import Dict, NamedTuple

import httpx

logger = logging.getLogger("talamala.pricing.feed")

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
FEED_TIMEOUT = 10  # seconds

# --- Sawiss (primary) ---------------------------------------------------------
SAWISS_BASE_URL = "https://sawiss.com"
SAWISS_AJAX_URL = f"{SAWISS_BASE_URL}/wp-admin/admin-ajax.php"
SAWISS_ACTION = "zioto_refresh_prices"
SAWISS_GOLD_KEY = "Gold750"    # 18K gold, purity 750 — matches Asset "gold_18k"
SAWISS_SILVER_KEY = "Silver999"  # matches PRECIOUS_METALS["silver"]["base_purity"] == 999

# The nonce is injected into the homepage as:
#   var ziotoPricing = {"ajax_url":"...","nonce":"4448d0ee63","refresh_url":"..."}
_SAWISS_NONCE_RE = re.compile(r"var\s+ziotoPricing\s*=\s*(\{.*?\});", re.S)

_sawiss_nonce: str | None = None
_sawiss_nonce_lock = threading.Lock()

# --- Goldis (fallback) --------------------------------------------------------
GOLDIS_PRICES_URL = "https://products.goldis.ir/api/v3/prices"


class PriceResult(NamedTuple):
    """A fetched price plus which upstream source produced it."""

    price: int  # rial per gram
    source: str  # "sawiss" | "goldis"


# ==============================================================================
# Sawiss
# ==============================================================================

def _fetch_sawiss_nonce(client: httpx.Client) -> str:
    """Scrape the WordPress nonce from the sawiss homepage and cache it."""
    global _sawiss_nonce

    resp = client.get(f"{SAWISS_BASE_URL}/", timeout=FEED_TIMEOUT)
    resp.raise_for_status()

    match = _SAWISS_NONCE_RE.search(resp.text)
    if not match:
        raise ValueError("ziotoPricing config not found on sawiss homepage (markup changed?)")

    try:
        nonce = json.loads(match.group(1))["nonce"]
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Could not parse nonce from ziotoPricing config: {e}") from e

    with _sawiss_nonce_lock:
        _sawiss_nonce = nonce
    return nonce


def _fetch_sawiss_prices() -> Dict[str, dict]:
    """
    Fetch all prices from sawiss.com in one HTTP call.

    Returns:
        dict mapping key → price entry
        e.g. {"Gold750": {"value_rial": 179550766, ...}, "Silver999": {...}}

    Raises:
        ValueError: If response is invalid.
        httpx.HTTPError: On network/HTTP errors.
    """
    with httpx.Client(headers={"User-Agent": BROWSER_USER_AGENT}, follow_redirects=True) as client:
        nonce = _sawiss_nonce or _fetch_sawiss_nonce(client)

        for attempt in range(2):
            resp = client.post(
                SAWISS_AJAX_URL,
                data={"action": SAWISS_ACTION, "nonce": nonce},
                timeout=FEED_TIMEOUT,
            )
            # An expired/invalid nonce is rejected with 400/403 — refresh it once and retry.
            if resp.status_code in (400, 403) and attempt == 0:
                logger.info("Sawiss rejected nonce (HTTP %s), refreshing", resp.status_code)
                nonce = _fetch_sawiss_nonce(client)
                continue
            break

        resp.raise_for_status()

    data = resp.json()
    if not data.get("success"):
        raise ValueError(f"Sawiss API returned success=false: {data}")
    if not isinstance(data.get("data"), dict):
        raise ValueError(f"Sawiss API missing 'data' dict: {data}")

    return data["data"]


def _sawiss_price(prices: Dict[str, dict], key: str) -> int:
    """Extract `value_rial` (the site's headline/sell price) for a given metal key."""
    entry = prices.get(key)
    if not entry:
        raise ValueError(f"Sawiss response has no '{key}' entry (keys: {list(prices)})")

    price = int(round(entry["value_rial"]))
    if price <= 0:
        raise ValueError(f"Invalid {key} price from sawiss: {price}")
    return price


# ==============================================================================
# Goldis (fallback)
# ==============================================================================

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
        headers={"User-Agent": BROWSER_USER_AGENT},
        timeout=FEED_TIMEOUT,
    )
    resp.raise_for_status()

    data = resp.json()
    if not data.get("success"):
        raise ValueError(f"Goldis API returned success=false: {data}")
    if not isinstance(data.get("data"), list):
        raise ValueError(f"Goldis API missing 'data' list: {data}")

    return {item["code"]: int(item["buy_price"]) for item in data["data"]}


def _goldis_price(prices: Dict[str, int], code: str) -> int:
    price = prices.get(code)
    if not price or price <= 0:
        raise ValueError(f"Invalid {code} price from goldis: {price}")
    return price


# ==============================================================================
# Public API — sawiss first, goldis as fallback
# ==============================================================================

def fetch_gold_price() -> PriceResult:
    """
    Fetch 18K gold price (purity 750), per gram in Rials.

    Tries sawiss.com first; falls back to goldis.ir if sawiss fails.

    Raises:
        ValueError / httpx.HTTPError: If BOTH sources fail (the sawiss error is re-raised).
    """
    try:
        price = _sawiss_price(_fetch_sawiss_prices(), SAWISS_GOLD_KEY)
        logger.info("Fetched gold 18K price from sawiss: %s rial", f"{price:,}")
        return PriceResult(price, "sawiss")
    except Exception as sawiss_error:
        logger.warning("Sawiss gold fetch failed (%s), falling back to goldis", sawiss_error)
        try:
            price = _goldis_price(_fetch_goldis_prices(), "GOLD18")
        except Exception as goldis_error:
            logger.error("Goldis gold fallback also failed: %s", goldis_error)
            raise sawiss_error from goldis_error

        logger.info("Fetched gold 18K price from goldis (fallback): %s rial", f"{price:,}")
        return PriceResult(price, "goldis")


def fetch_silver_price() -> PriceResult:
    """
    Fetch silver price (purity 999), per gram in Rials.

    Tries sawiss.com first; falls back to goldis.ir if sawiss fails.

    Raises:
        ValueError / httpx.HTTPError: If BOTH sources fail (the sawiss error is re-raised).
    """
    try:
        price = _sawiss_price(_fetch_sawiss_prices(), SAWISS_SILVER_KEY)
        logger.info("Fetched silver price from sawiss: %s rial", f"{price:,}")
        return PriceResult(price, "sawiss")
    except Exception as sawiss_error:
        logger.warning("Sawiss silver fetch failed (%s), falling back to goldis", sawiss_error)
        try:
            price = _goldis_price(_fetch_goldis_prices(), "SILVER")
        except Exception as goldis_error:
            logger.error("Goldis silver fallback also failed: %s", goldis_error)
            raise sawiss_error from goldis_error

        logger.info("Fetched silver price from goldis (fallback): %s rial", f"{price:,}")
        return PriceResult(price, "goldis")
