"""
Unit tests for signal gating logic in Elon Rotation Bot.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from signals.gating import should_send


def test_initial_send():
	now = datetime.now(timezone.utc)
	send, reason = should_send({"BTC": 0.6}, None, {}, None, None, now)
	assert send and reason == "initial"


def test_debounce():
	now = datetime.now(timezone.utc)
	last = now - timedelta(minutes=30)
	prev = {"BTC": 0.34, "ETH": 0.33, "ALTS": 0.33}
	send, reason = should_send(prev, prev, {}, {}, last, now)
	assert not send and reason == "debounce"


def test_force():
	now = datetime.now(timezone.utc)
	last = now - timedelta(days=1)
	prev = {"BTC": 0.34}
	send, reason = should_send(prev, prev, {}, {}, last, now, force=True)
	assert send and reason == "force"


def test_weight_change():
	now = datetime.now(timezone.utc)
	last = now - timedelta(days=1)
	prev = {"BTC": 0.20, "ETH": 0.4, "ALTS": 0.4}
	target = {"BTC": 0.35, "ETH": 0.33, "ALTS": 0.32}
	send, reason = should_send(target, prev, {}, {}, last, now)
	assert send and reason.startswith("weight_change")


def test_pi_cycle_toggle():
	now = datetime.now(timezone.utc)
	last = now - timedelta(days=1)
	prev = {"BTC": 0.34}
	prev_ind = {"pi_cycle_flag": False}
	cur_ind = {"pi_cycle_flag": True}
	send, reason = should_send(prev, prev, cur_ind, prev_ind, last, now)
	assert send and reason == "pi_cycle_toggle"


def test_threshold_crossing():
	now = datetime.now(timezone.utc)
	last = now - timedelta(days=1)
	prev = {"BTC": 0.34}
	prev_ind = {"cbbi": 69}
	cur_ind = {"cbbi": 71}
	send, reason = should_send(prev, prev, cur_ind, prev_ind, last, now)
	assert send and reason.startswith("cross_cbbi")

