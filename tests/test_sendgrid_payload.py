from notify.sendgrid_payload import build_dynamic_template_data

def test_build_dynamic_template_data_minimal():
    before = {"BTC": 0.5, "ETH": 0.3, "ALTS": 0.2}
    after = {"BTC": 0.4, "ETH": 0.4, "ALTS": 0.2}
    indicators = {"btc_dom": 55, "fear_greed": 40, "cbbi": 12, "pi_cycle_flag": True, "risk": "test risk"}
    data = build_dynamic_template_data(before, after, indicators)
    assert data["action"] == "rotate"
    assert data["tldr"].startswith("Rotate")
    assert isinstance(data["rows"], list) and len(data["rows"]) == 3
    assert "BTC" in [r["asset"] for r in data["rows"]]
    assert data["why"] and "BTC.D" in data["why"][0]
    assert data["risk"] == "test risk"
