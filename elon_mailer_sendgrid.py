#!/usr/bin/env python3
"""
Elon Rotation Bot — SendGrid HTTP Mailer (no Gmail App Password needed)

Setup (one-time):
1) Create a free SendGrid account (single sender is fine).
2) Verify your From email (e.g., barryaburnett@gmail.com) under "Sender Authentication" → "Single Sender".
3) Create an API Key with "Mail Send" permission.
4) Export env vars (e.g., in ~/.zprofile) — store real keys in your shell/private vault, do NOT commit them to git:
    export ***REMOVED***
    export ELON_FROM_EMAIL="barryaburnett@gmail.com"
    export ELON_FROM_NAME="Elon Rotation Bot"

Send a test (no change):
   python elon_mailer_sendgrid.py --action no_change --to barryaburnett@gmail.com
"""

import os
import json
import argparse
import base64
from datetime import datetime, timezone
import urllib.request
import urllib.error

import matplotlib.pyplot as plt

API_URL = "https://api.sendgrid.com/v3/mail/send"

def make_pie(data, title, filename):
    labels = list(data.keys())
    sizes  = list(data.values())
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    plt.title(title)
    plt.savefig(filename, dpi=200, bbox_inches='tight')
    plt.close(fig)

def b64_file(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')

def send_via_sendgrid(subject, html_body, attachments, to_email, from_email, from_name, api_key):
    # Build attachments payload
    atts = []
    for path in attachments:
        atts.append({
            "content": b64_file(path),
            "type": "image/png",
            "filename": os.path.basename(path),
            "disposition": "attachment"
        })

    data = {
        "personalizations": [{
            "to": [{"email": to_email}],
            "subject": subject
        }],
        "from": {"email": from_email, "name": from_name},
        "content": [{"type": "text/html", "value": html_body}],
        "attachments": atts
    }

    req = urllib.request.Request(API_URL, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    body = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, body) as resp:
            # 202 is success for SendGrid
            if resp.status not in (200, 202):
                raise SystemExit(f"SendGrid error: HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"SendGrid error {e.code}: {msg}")

def main():
    parser = argparse.ArgumentParser(description="Send Elon Rotation Bot email via SendGrid API")
    parser.add_argument('--to', default='barryaburnett@gmail.com', help='Recipient email')
    parser.add_argument('--action', choices=['rotate','no_change'], required=True, help='Action for this email')
    parser.add_argument('--from_alloc', default='{\"BTC\":69.44, \"ETH\":16.50, \"ALTs\":14.06}', help='JSON of before allocation %')
    parser.add_argument('--to_alloc',   default='{\"BTC\":69.44, \"ETH\":16.50, \"ALTs\":14.06}', help='JSON of after allocation %')
    parser.add_argument('--increase',   default='[]', help='JSON list e.g. [{\"asset\":\"ETH\",\"delta_pct_points\":3}]')
    parser.add_argument('--reduce',     default='[]', help='JSON list e.g. [{\"asset\":\"BTC\",\"delta_pct_points\":3}]')
    parser.add_argument('--why',        default='[\"BTC dominance stable; alt breadth muted\",\"ETH/BTC not leading\",\"Elevated sentiment without confirmation\"]', help='JSON list of up to 3 bullets')
    parser.add_argument('--risk',       default='Rotate on BTC.D ±1% with alt breadth or decisive ETH/BTC breakout with follow-through', help='Risk & invalidation text')
    parser.add_argument('--next_hours', type=int, default=4, help='Next checkpoint in hours')
    args = parser.parse_args()

    API_KEY    = os.environ.get('SENDGRID_API_KEY')
    FROM_EMAIL = os.environ.get('ELON_FROM_EMAIL', 'barryaburnett@gmail.com')
    FROM_NAME  = os.environ.get('ELON_FROM_NAME', 'Elon Rotation Bot')

    if not API_KEY:
        raise SystemExit("Missing SENDGRID_API_KEY env var. See script header for setup.")

    from_alloc = json.loads(args.from_alloc)
    to_alloc   = json.loads(args.to_alloc)
    increase   = json.loads(args.increase)
    reduce     = json.loads(args.reduce)
    why_list   = json.loads(args.why)

    today = datetime.now().date().isoformat()
    date_tag = datetime.now().strftime('%Y%m%d')

    # Generate pies
    before_png = f'allocation_before_{date_tag}.png'
    after_png  = f'allocation_after_{date_tag}.png'
    make_pie(from_alloc, f'Allocation Before — {today}', before_png)
    make_pie(to_alloc,   f'Allocation After — {today}',  after_png)

    def row(asset, a, b):
        return f"<tr><td>{asset}</td><td style='text-align:right'>{a:.2f}%</td><td style='text-align:right'>{b:.2f}%</td></tr>"

    table_html = f"""
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
      <tr><th>Asset</th><th>Before</th><th>After</th></tr>
      {row('BTC', from_alloc.get('BTC',0), to_alloc.get('BTC',0))}
      {row('ETH', from_alloc.get('ETH',0), to_alloc.get('ETH',0))}
      {row('ALTs',from_alloc.get('ALTs',0),to_alloc.get('ALTs',0))}
    </table>
    """

    if args.action == 'rotate':
        from_asset = reduce[0]['asset'] if reduce else 'BTC'
        to_asset   = increase[0]['asset'] if increase else 'ETH'
        delta_pp   = (increase[0]['delta_pct_points'] if increase else 0)
        tldr = f'“Rotate {delta_pp:.0f}% from {from_asset} to {to_asset} now.”'
        action_str = 'Rotate'
    else:
        tldr = 'No change — hold current allocations.'
        action_str = 'No Change'

    why_html = '<br>'.join(f'- {w}' for w in why_list[:3])

    json_block = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec='seconds'),
        "window": "08:00-20:00 Europe/London",
        "action": "rotate" if args.action=='rotate' else "no_change",
        "from_allocation_pct": from_alloc,
        "to_allocation_pct": to_alloc,
        "increase": increase,
        "reduce": reduce,
        "rationale_top_signals": why_list[:3],
        "risk_invalidation": args.risk,
        "next_checkpoint_hours": args.next_hours
    }
    json_str = json.dumps(json_block, ensure_ascii=False, indent=2)

    subject = f"Rotation Update — {today} — {action_str}: BTC→ETH→ALTs"

    html_body = f"""
    <div>To: {args.to}</div>
    <div>From: Elon Rotation Bot</div>
    <div><b>Subject:</b> Rotation Update — {today} — <b>{action_str}</b>: BTC→ETH→ALTs</div>
    <br>
    <div><b>TL;DR</b>: {tldr}</div>
    <br>
    <div><b>Allocation — Before vs After</b></div>
    {table_html}
    <br>
    <div>Attach: allocation_before_{date_tag}.png, allocation_after_{date_tag}.png</div>
    <br>
    <div><b>Action List</b></div>
    <div>Increase: {"; ".join([f"{x['asset']} +{x['delta_pct_points']} pp" for x in increase]) or "—"}</div>
    <div>Reduce: {"; ".join([f"{x['asset']} -{x['delta_pct_points']} pp" for x in reduce]) or "—"}</div>
    <div>(Loop respected: BTC → ETH → ALTs → BTC)</div>
    <br>
    <div><b>Why (max 3 bullets)</b></div>
    <div>{why_html or "—"}</div>
    <br>
    <div><b>Risk & Invalidation</b></div>
    <div>{args.risk}</div>
    <br>
    <div><b>Next Checkpoint</b></div>
    <div>Re‑evaluate in {args.next_hours}h or on BTC.D ±1% move.</div>
    <br>
    <pre style="font-family:monospace; white-space:pre-wrap">{json_str}</pre>
    """

    send_via_sendgrid(
        subject=subject,
        html_body=html_body,
        attachments=[before_png, after_png],
        to_email=args.to,
        from_email=FROM_EMAIL,
        from_name=FROM_NAME,
        api_key=REDACTED
    )

    print("Email sent via SendGrid.")

if __name__ == "__main__":
    main()
