"""Tests for notify/emailer.py compose function."""
from notify.emailer import compose_email


def test_compose_email_creates_attachments(tmp_path):
    before = {"BTC": 0.5, "ETH": 0.3, "ALTS": 0.2}
    after = {"BTC": 0.6, "ETH": 0.25, "ALTS": 0.15}
    indicators = {"btc_dom": 55, "fear_greed": 40, "cbbi": 68}
    subject, html, attachments = compose_email(before, after, indicators)
    assert "Elon Rotation Update" in subject
    assert "Actions:" in html
    # attachments should be two png paths
    assert len(attachments) == 2
    for p in attachments:
        assert p.endswith('.png')
        # file exists
        with open(p, 'rb') as fh:
            data = fh.read()
        assert len(data) > 0
