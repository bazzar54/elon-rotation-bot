# rotation/allocator.py
from __future__ import annotations

MIN_W = 0.05
MAX_W = 0.80

def _clamp(x: float, lo: float = MIN_W, hi: float = MAX_W) -> float:
    return max(lo, min(hi, x))

def _normalize(w: dict[str, float]) -> dict[str, float]:
    s = sum(w.values()) or 1.0
    return {k: round(v / s, 2) for k, v in w.items()}

def allocate(ind: dict) -> dict[str, float]:
    """
    Allocation logic for Elon Rotation Bot.
    Rules (summarised):
      - Risk-off: btc_dom > 55 AND fear_greed < 35  => BTC >= 0.60, ETH <= 0.25
      - Risk-on alts: fg > 65 AND btc_dom < 50 AND cbbi < 75 => ALTS >= 0.45
      - ETH rotation: trend_eth == 'up' AND btc_dom_delta_7d <= -1.0 => ETH >= 0.35
      - Top risk cap: if pi_cycle_flag or cbbi >= 90 => ALTS <= 0.20 and ETH <= 0.35
      - Guardrails: each in [0.05, 0.80]; final weights sum to 1.00 (rounded 2 dp)
    """
    btc_dom = float(ind.get("btc_dom", 50.0))
    fg = float(ind.get("fear_greed", 50.0))
    cbbi = float(ind.get("cbbi", 60.0))
    trend_eth = (ind.get("trend_eth") or "").lower()
    btc_dom_delta_7d = float(ind.get("btc_dom_delta_7d", 0.0))
    pi_cycle_flag = bool(ind.get("pi_cycle_flag", False))

    # start near-even
    w = {"BTC": 0.34, "ETH": 0.33, "ALTS": 0.33}

    # ---- Risk-on alts (do this early so later caps can still restrict) ----
    if fg > 65 and btc_dom < 50 and cbbi < 75:
        # push ALTS high per rule
        w["ALTS"] = max(w["ALTS"], 0.45)
        # split leftover between BTC/ETH with slight ETH bias
        leftover = max(0.0, 1.0 - w["ALTS"])
        w["ETH"] = max(MIN_W, min(0.30, leftover * 0.55))
        w["BTC"] = max(MIN_W, leftover - w["ETH"])

    # ---- ETH rotation boost ----
    if trend_eth == "up" and btc_dom_delta_7d <= -1.0:
        w["ETH"] = max(w["ETH"], 0.35)
        # rebalance BTC vs ALTS from remaining
        rem = max(0.0, 1.0 - w["ETH"])
        # keep ALTS share unless risk-off overrides later
        keep_alts = min(w["ALTS"], rem - MIN_W)
        keep_alts = max(MIN_W, keep_alts)
        w["ALTS"] = keep_alts
        w["BTC"] = max(MIN_W, rem - w["ALTS"])

    # ---- Risk-off tilt to BTC ----
    if btc_dom > 55 and fg < 35:
        w["BTC"] = max(w["BTC"], 0.60)
        # cap ETH as per rule; give the rest to ALTS but keep guardrails
        w["ETH"] = min(w["ETH"], 0.25)
        rem = max(0.0, 1.0 - w["BTC"] - w["ETH"])
        w["ALTS"] = max(MIN_W, min(MAX_W, rem))

    # ---- Top risk cap (after boosts) ----
    if pi_cycle_flag or cbbi >= 90:
        w["ALTS"] = min(w["ALTS"], 0.20)
        w["ETH"] = min(w["ETH"], 0.35)
        # push any excess back to BTC within caps
        rem = max(0.0, 1.0 - w["ETH"] - w["ALTS"])
        w["BTC"] = max(MIN_W, min(MAX_W, rem))

    # final guardrails + normalize
    w = {k: _clamp(v) for k, v in w.items()}
    return _normalize(w)
