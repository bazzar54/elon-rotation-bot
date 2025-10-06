"""Gating logic for whether to send an email update.

Function should_send compares target weights to previously sent weights and
indicator state, applies major-flag rules and a debounce window.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple


MAJOR_CROSS_THRESHOLDS = {
    "cbbi": (70, 90),
    "fear_greed": (35, 65),
    "btc_dom": (50, 55),
}


def _max_abs_diff(a: Dict[str, float], b: Dict[str, float]) -> float:
    keys = set(a) | set(b)
    return max(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys)


def _crossed(prev: Optional[float], cur: Optional[float], threshold: float) -> bool:
    if prev is None or cur is None:
        return False
    return (prev < threshold <= cur) or (prev >= threshold > cur)


def should_send(
    target: Dict[str, float],
    prev_weights: Optional[Dict[str, float]],
    indicators: Dict,
    prev_indicators: Optional[Dict],
    last_sent_at: Optional[datetime],
    now: datetime,
    force: bool = False,
) -> Tuple[bool, str]:
    """Decide whether to send an email update.

    Returns (send: bool, reason: str)
    """
    # Force overrides everything
    if force:
        return True, "force"

    # If no previous weights/timestamp, send initial
    if prev_weights is None or last_sent_at is None:
        return True, "initial"

    # Debounce: require >= 2 hours since last_sent
    if now - last_sent_at < timedelta(hours=2):
        return False, "debounce"

    # weight change threshold (10% absolute)
    maxdiff = _max_abs_diff(target, prev_weights)
    if maxdiff >= 0.10:
        return True, f"weight_change:{maxdiff:.2f}"

    # Major flag toggles or threshold crossings
    # pi_cycle toggled
    prev_pi = bool(prev_indicators.get("pi_cycle_flag", False)) if prev_indicators else False
    cur_pi = bool(indicators.get("pi_cycle_flag", False))
    if prev_pi != cur_pi:
        return True, "pi_cycle_toggle"

    # Check threshold crossings for cbbi, fear_greed, btc_dom
    if prev_indicators:
        for k, (low, high) in MAJOR_CROSS_THRESHOLDS.items():
            prev_v = prev_indicators.get(k)
            cur_v = indicators.get(k)
            # crossing low or high
            if _crossed(prev_v, cur_v, low) or _crossed(prev_v, cur_v, high):
                return True, f"cross_{k}"

    # No signal
    return False, "no_signal"