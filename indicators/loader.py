"""Indicators loader for Elon Rotation Bot.
This implementation queries public endpoints for live-ish data.

Sources used:
- CoinGecko Global endpoint for market cap percentages (btc_dom, eth_dom)
- CoinGecko market_chart for short-term ETH trend
- alternative.me Fear & Greed Index for sentiment

The function is robust to network failures and returns reasonable
fallback values plus an optional `source_errors` list with diagnostics.
"""
from datetime import datetime, timedelta, timezone
import time
import json
import urllib.request
import urllib.error
from typing import Dict
from pathlib import Path


CACHE_FN = Path("state") / "indicators_cache.json"


COINGECKO_GLOBAL = "https://api.coingecko.com/api/v3/global"
COINGECKO_MARKET_CHART = "https://api.coingecko.com/api/v3/coins/{id}/market_chart?vs_currency=usd&days={days}"
FNG_API = "https://api.alternative.me/fng/?limit=1"


def _fetch_json(url: str, timeout: int = 10, retries: int = 2, backoff: float = 0.7):
    """Fetch JSON with a tiny retry loop for transient failures.

    Returns a dict on success or a dict with key "_error" on failure.
    """
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_exc = exc
            # short backoff before retrying
            if attempt < retries:
                time.sleep(backoff)
    return {"_error": str(last_exc)}


def _eth_trend_from_prices(prices: list) -> str:
    # prices: list of [timestamp, price]
    if not prices or len(prices) < 2:
        return "flat"
    start = prices[0][1]
    end = prices[-1][1]
    pct = (end - start) / start if start else 0.0
    if pct > 0.01:
        return "up"
    if pct < -0.01:
        return "down"
    return "flat"


def load_indicators(now_utc: datetime, *, no_network: bool = False, cache_ttl: int = 120) -> Dict:
    """Return indicators, attempting live fetches and falling back on defaults.

    Returns keys used by the rest of the app (btc_dom, eth_dom, fear_greed, cbbi,
    trend_btc, trend_eth, pi_cycle_flag, btc_dom_delta_7d) and an optional
    `source_errors` list with short diagnostics.
    """
    errors = []
    using_cache = False

    # sensible defaults (ensure this exists for no_network paths)
    indicators: Dict = {
        "btc_dom": None,
        "eth_dom": None,
        "fear_greed": None,
        "cbbi": None,
        "trend_btc": "flat",
        "trend_eth": "flat",
        "pi_cycle_flag": False,
        "gtrends_coinbase": None,
        "btc_dom_delta_7d": None,
    }

    # Try reading cache first
    try:
        if CACHE_FN.exists():
            raw = json.loads(CACHE_FN.read_text())
            cached_at = raw.get("cached_at")
            if cached_at:
                try:
                    cached_ts = datetime.fromisoformat(cached_at)
                    age = (now_utc - cached_ts).total_seconds()
                    if age <= cache_ttl:
                        using_cache = True
                        indicators = raw.get("indicators", {})
                        indicators["_cached_at"] = cached_at
                        indicators["_cache_age"] = age
                        return indicators
                except Exception as exc:
                    errors.append(f"cache_parse:{exc}")
    except Exception as exc:
        errors.append(f"cache_read:{exc}")

    if no_network:
        # Return defaults (ensuring numeric required keys)
        if errors:
            indicators["source_errors"] = errors
        if indicators["btc_dom"] is None:
            indicators["btc_dom"] = 55.0
        if indicators["eth_dom"] is None:
            indicators["eth_dom"] = 18.0
        if indicators["fear_greed"] is None:
            indicators["fear_greed"] = 40
        if indicators.get("cbbi") is None:
            indicators["cbbi"] = 65
        if indicators.get("btc_dom_delta_7d") is None:
            indicators["btc_dom_delta_7d"] = 0.0
        if indicators.get("gtrends_coinbase") is None:
            indicators["gtrends_coinbase"] = 50
        return indicators
    # (indicators already initialized above)

    # 1) CoinGecko global for market cap percentages
    g = _fetch_json(COINGECKO_GLOBAL)
    if "_error" in g:
        errors.append(f"coingecko_global:{g['_error']}")
    else:
        try:
            mc_pct = g.get("data", {}).get("market_cap_percentage", {})
            btc = mc_pct.get("btc")
            eth = mc_pct.get("eth")
            if btc is not None:
                indicators["btc_dom"] = round(float(btc), 2)
            if eth is not None:
                indicators["eth_dom"] = round(float(eth), 2)
        except Exception as exc:
            errors.append(f"coingecko_parse:{exc}")

    # 2) ETH short term trend (7 days)
    eth_chart = _fetch_json(COINGECKO_MARKET_CHART.format(id="ethereum", days=7))
    if "_error" in eth_chart:
        errors.append(f"coingecko_eth_chart:{eth_chart['_error']}")
    else:
        prices = eth_chart.get("prices") or []
        indicators["trend_eth"] = _eth_trend_from_prices(prices)

    # 3) Fear & Greed index (alternative.me)
    fng = _fetch_json(FNG_API)
    if "_error" in fng:
        errors.append(f"fng:{fng['_error']}")
    else:
        try:
            data = fng.get("data")
            if data and isinstance(data, list) and len(data) > 0:
                latest = data[0]
                indicators["fear_greed"] = int(latest.get("value", 0))
        except Exception as exc:
            errors.append(f"fng_parse:{exc}")

    # 4) btc_dom delta 7d: approximate using CoinGecko global historical isn't available
    # so leave as None for now.

    # Attach any errors for visibility
    if errors:
        indicators["source_errors"] = errors

    # Fallback to fixed defaults if essential values are still None
    if indicators["btc_dom"] is None:
        indicators["btc_dom"] = 55.0
    if indicators["eth_dom"] is None:
        indicators["eth_dom"] = 18.0
    if indicators["fear_greed"] is None:
        indicators["fear_greed"] = 40

    # Ensure numeric fields used by allocator are not None
    if indicators.get("cbbi") is None:
        indicators["cbbi"] = 65
    if indicators.get("btc_dom_delta_7d") is None:
        indicators["btc_dom_delta_7d"] = 0.0
    if indicators.get("gtrends_coinbase") is None:
        indicators["gtrends_coinbase"] = 50

    return indicators

