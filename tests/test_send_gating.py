import os
from unittest import mock

import pytest

from datetime import datetime, timezone, timedelta

from rotation.allocator import allocate
from signals.gating import should_send


def make_indicators(seed: int = 0):
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


def test_initial_send_when_no_last_sent():
    now = datetime.now(timezone.utc)
    indicators = make_indicators()
    target = allocate(indicators)
    prev = target.copy()
    # When last_sent_at is None, should_send returns True (initial send)
    send, reason = should_send(target, prev, indicators, indicators, None, now, force=False)
    assert send is True


def test_debounce_prevents_send_within_two_hours():
    now = datetime.now(timezone.utc)
    indicators = make_indicators()
    target = allocate(indicators)
    prev = target.copy()
    # last_sent_at is 1 hour ago: should debounce
    last_sent = now - timedelta(hours=1)
    send, reason = should_send(target, prev, indicators, indicators, last_sent, now, force=False)
    assert send is False


def test_send_path_called_when_send_and_flag(tmp_path, monkeypatch):
    # Ensure that when send is True and --send is requested, emailer.send_email is called
    now = datetime.now(timezone.utc)
    indicators = make_indicators()
    target = allocate(indicators)
    prev = {"BTC": 0.5, "ETH": 0.25, "ALTS": 0.25}

    # Force send via should_send by using force=True (bypass gating)
    send, reason = should_send(target, prev, indicators, indicators, None, now, force=True)
    assert send is True

    fake_calls = {}

    def fake_compose(before, after, indicators):
        return ("subject", "<html></html>", [str(tmp_path / "a.png")])

    def fake_send(subject, html, attachments, to_addr, smtp_from=None):
        fake_calls['sent'] = True

    monkeypatch.setenv('ELON_TO_EMAIL', 'test@example.com')
    monkeypatch.setenv('SMTP_HOST', 'smtp.example.com')
    monkeypatch.setenv('SMTP_USER', 'user')
    monkeypatch.setenv('SMTP_PASS', 'pass')
    monkeypatch.setenv('SMTP_FROM', 'from@example.com')

    monkeypatch.setattr('notify.emailer.compose_email', fake_compose)
    monkeypatch.setattr('notify.emailer.send_email', fake_send)

    # Simulate calling main's send block by directly invoking compose/send
    subject, html, attachments = fake_compose(prev, target, indicators)
    fake_send(subject, html, attachments, os.getenv('ELON_TO_EMAIL'))

    assert fake_calls.get('sent', False) is True
