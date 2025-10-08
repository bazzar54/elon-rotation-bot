from datetime import datetime
from typing import Dict

def build_dynamic_template_data(before: Dict[str, float], after: Dict[str, float], indicators: Dict) -> Dict:
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    action = "no_change"
    tldr = "No change — hold current allocations."
    rows = []
    for k in ["BTC", "ETH", "ALTS"]:
        b = before.get(k, 0.0)
        a = after.get(k, 0.0)
        rows.append({"asset": k, "before": round(b * 100, 2), "after": round(a * 100, 2)})
        if abs(a - b) >= 0.001:
            action = "rotate"
    if action == "rotate":
        tldr = "Rotate per attached allocation."

    why = []
    if indicators.get("btc_dom") is not None and indicators.get("fear_greed") is not None:
        why.append(f"BTC.D {indicators.get('btc_dom')} pp; Fear&Greed {indicators.get('fear_greed')}")
    if indicators.get("pi_cycle_flag"):
        why.append("Pi-Cycle flagged")
    if indicators.get("cbbi") is not None:
        why.append(f"CBBI {indicators.get('cbbi')}")

    risk = indicators.get("risk", "") or ""

    return {
        "date": now,
        "action": action,
        "tldr": tldr,
        "rows": rows,
        "why": why,
        "risk": risk,
    }

__all__ = ["build_dynamic_template_data"]
