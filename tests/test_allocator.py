"""
Unit tests for allocator logic in Elon Rotation Bot.
"""
import pytest
from rotation.allocator import allocate

def test_risk_off():
    indicators = {"btc_dom": 58, "fear_greed": 28}
    weights = allocate(indicators)
    assert weights["BTC"] >= 0.60

def test_eth_rotation():
    indicators = {"trend_eth": "up", "btc_dom_delta_7d": -1.2}
    weights = allocate(indicators)
    assert weights["ETH"] >= 0.35

def test_risk_on_alts():
    indicators = {"fear_greed": 72, "btc_dom": 48, "cbbi": 60}
    weights = allocate(indicators)
    assert weights["ALTS"] >= 0.45

def test_top_risk():
    indicators = {"pi_cycle_flag": True, "cbbi": 91}
    weights = allocate(indicators)
    assert weights["ALTS"] <= 0.20
    assert weights["ETH"] <= 0.35

def test_clamp_normalize():
    indicators = {"btc_dom": 40, "fear_greed": 80, "cbbi": 10}
    weights = allocate(indicators)
    assert sum(weights.values()) == pytest.approx(1.00, abs=0.01)
    for v in weights.values():
        assert 0.05 <= v <= 0.80
