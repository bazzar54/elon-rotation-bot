"""
Indicators loader for Elon Rotation Bot.
Implements load_indicators(now_utc) -> dict.
"""
from datetime import datetime

def load_indicators(now_utc: datetime) -> dict:
    """Fetch and return all required indicators as a dict.
    Args:
        now_utc (datetime): Current UTC datetime.
    Returns:
        dict: Indicator values.
    """
    # TODO: Implement indicator fetching
    return {
        "btc_dom": 55.0,
        "eth_dom": 18.0,
        "fear_greed": 40,
        "cbbi": 65,
        "trend_btc": "flat",
        "trend_eth": "up",
        "pi_cycle_flag": False,
        "gtrends_coinbase": 50,
        "btc_dom_delta_7d": 1.2,
    }
