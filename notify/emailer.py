"""Email composer for Elon Rotation Bot.
Builds small HTML rotation updates and optionally sends them via SMTP.

This module provides two functions:
- compose_email(before, after, indicators, portfolio=None) -> (subject, html, [attachments])
- send_email(subject, html, attachments, to_address, smtp_from=None)

Attachments are generated as PNG pie charts in /tmp.
"""

from datetime import datetime, timezone
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
from dotenv import load_dotenv


load_dotenv()


def _make_pie(weights: Dict[str, float], title: str, path: str) -> None:
    labels = list(weights.keys())
    vals = [weights.get(k, 0.0) for k in labels]
    pct = [v * 100 for v in vals]
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.pie(pct, labels=labels, autopct="%1.0f%%", startangle=140)
    ax.set_title(title)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def compose_email(
    before: Dict[str, float],
    after: Dict[str, float],
    indicators: Dict,
    portfolio: Optional[Dict] = None,
) -> Tuple[str, str, List[str]]:
    """Compose a short HTML email and generate two pie-chart attachments.

    Returns (subject, html_body, [attachment_paths]).
    """
    now = datetime.now(timezone.utc)
    subject = f"Elon Rotation Update — {now.strftime('%Y-%m-%d %H:%M UTC')}"

    bullets: List[str] = []
    if indicators.get("btc_dom") is not None and indicators.get("fear_greed") is not None:
        bullets.append(f"BTC.D {indicators.get('btc_dom')} pp; Fear&Greed at {indicators.get('fear_greed')}")
    if indicators.get("cbbi") is not None:
        bullets.append(f"CBBI {indicators.get('cbbi')}")
    if indicators.get("pi_cycle_flag"):
        bullets.append("Pi-Cycle flagged")

    table_rows = """
<tr><th>Asset</th><th>Before</th><th>After</th></tr>
"""
    for k in ["BTC", "ETH", "ALTS"]:
        b = before.get(k, 0.0)
        a = after.get(k, 0.0)
        table_rows += f"<tr><td>{k}</td><td>{b:.0%}</td><td>{a:.0%}</td></tr>\n"

    actions = []
    for k in ["BTC", "ETH", "ALTS"]:
        diff = round((after.get(k, 0.0) - before.get(k, 0.0)) * 100)
        sign = "+" if diff >= 0 else ""
        actions.append(f"{sign}{diff}% {k}")

    html = f"""
<html>
<body>
  <h2>{subject}</h2>
  <ul>
    {''.join(f'<li>{b}</li>' for b in bullets)}
  </ul>
  <table border="1" cellpadding="4" cellspacing="0">
    {table_rows}
  </table>
  <p><strong>Actions:</strong> {', '.join(actions)}</p>
</body>
</html>
"""

    ts = int(now.timestamp())
    before_path = f"/tmp/elon_email_before_{ts}.png"
    after_path = f"/tmp/elon_email_after_{ts}.png"
    _make_pie(before, "Before", before_path)
    _make_pie(after, "After", after_path)

    return subject, html, [before_path, after_path]


def send_email(
    subject: str,
    html_body: str,
    attachments: List[str],
    to_address: str,
    smtp_from: Optional[str] = None,
) -> None:
    """Send an HTML email with attachments using SMTP credentials from environment.

    Required env vars: SMTP_HOST, SMTP_USER, SMTP_PASS, SMTP_FROM (unless smtp_from provided).
    Optional: SMTP_PORT (default 587).
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = smtp_from or os.getenv("SMTP_FROM")

    if not smtp_host or not smtp_user or not smtp_pass or not smtp_from:
        raise RuntimeError("SMTP credentials are not fully configured in environment")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_address
    msg.set_content("This is an HTML email. Please view in an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")

    for path in attachments:
        with open(path, "rb") as f:
            data = f.read()
        msg.add_attachment(data, maintype="image", subtype="png", filename=Path(path).name)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as s:
        s.starttls()
        s.login(smtp_user, smtp_pass)
        s.send_message(msg)


__all__ = ["compose_email", "send_email"]
