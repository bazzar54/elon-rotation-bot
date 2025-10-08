"""
CLI entrypoint for Elon Rotation Bot.
Implements a minimal runner used for dry-runs: loads indicators, allocates,
optionally saves indicators, writes before/after pie charts to /tmp, and logs the run.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Dict

import matplotlib.pyplot as plt

from indicators.loader import load_indicators
from rotation.allocator import allocate
from signals.gating import should_send
from dotenv import load_dotenv


load_dotenv()


STATE_DIR = Path("state")
LOGS_DIR = Path("logs")
STATE_FILE = STATE_DIR / "last_sent.json"


def read_last_sent() -> Dict[str, float] | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return None


def write_last_sent(w: Dict[str, float]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(w, indent=2, default=str))


def save_indicators(path: str, indicators: dict) -> None:
    p = Path(path)
    p.write_text(json.dumps(indicators, indent=2, default=str))


def pie_chart(weights: Dict[str, float], title: str, path: str) -> None:
    labels = list(weights.keys())
    vals = [weights[k] for k in labels]
    # Matplotlib expects sums in 1.0 or 100; use percentages
    pct = [v * 100 for v in vals]
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.pie(pct, labels=labels, autopct="%1.0f%%", startangle=140)
    ax.set_title(title)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def printable_change(before: Dict[str, float], after: Dict[str, float]) -> str:
    parts = []
    for k in ["BTC", "ETH", "ALTS"]:
        b = before.get(k, 0.0)
        a = after.get(k, 0.0)
        diff = round((a - b) * 100, 0)
        sign = "+" if diff >= 0 else ""
        parts.append(f"{sign}{int(diff)}% {k}")
    return ", ".join(parts)


def log_run(msg: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fn = LOGS_DIR / f"run-{datetime.now(timezone.utc).date().isoformat()}.txt"
    with fn.open("a") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Elon Rotation Bot")
    parser.add_argument("--dry-run", action="store_true", help="No email sent")
    parser.add_argument("--send", action="store_true", help="Actually send email if gating allows")
    parser.add_argument("--force", action="store_true", help="Bypass gating")
    parser.add_argument("--save-indicators", type=str, help="Save indicators to path.json")
    parser.add_argument("--no-network", action="store_true", help="Use cache only; do not perform network fetches")
    parser.add_argument("--cache-ttl", type=int, default=120, help="Indicators cache TTL in seconds")
    args = parser.parse_args()

    # runtime report (no secrets)
    print(f"SendGrid? {bool(os.getenv('SENDGRID_API_KEY'))}; SMTP? {all(os.getenv(k) for k in ['SMTP_HOST','SMTP_PORT','SMTP_USER','SMTP_PASS','SMTP_FROM'])}")

    now_utc = datetime.now(timezone.utc)
    indicators = load_indicators(now_utc, no_network=args.no_network, cache_ttl=args.cache_ttl)
    target = allocate(indicators)

    # last sent (structured: {"weights":..., "indicators":..., "sent_at": iso})
    raw = read_last_sent()
    prev_weights = None
    prev_indicators = None
    last_sent_at = None
    if raw:
        prev_weights = raw.get("weights")
        prev_indicators = raw.get("indicators")
        sent_at = raw.get("sent_at")
        try:
            last_sent_at = datetime.fromisoformat(sent_at) if sent_at else None
        except Exception:
            last_sent_at = None
    if prev_weights is None:
        prev_weights = target.copy()

    # Save indicators if requested
    if args.save_indicators:
        save_indicators(args.save_indicators, {"generated_at": now_utc.isoformat(), **indicators})

    # Generate pie charts in /tmp
    before_path = f"/tmp/elon_before_{int(now_utc.timestamp())}.png"
    after_path = f"/tmp/elon_after_{int(now_utc.timestamp())}.png"
    try:
        pie_chart(prev_weights, "Before", before_path)
        pie_chart(target, "After", after_path)
    except Exception as exc:
        print("Failed to generate charts:", exc)

    # Decide whether to send (gating)
    send, reason = should_send(target, prev_weights, indicators, prev_indicators, last_sent_at, now_utc, force=args.force)

    # Print concise summary
    london = now_utc.astimezone(ZoneInfo("Europe/London"))
    title = f"Elon Rotation Update — {london.strftime('%Y-%m-%d %H:%M UK')}"
    print(title)
    # short rationale bullets (simple derivation)
    rationale = []
    btc_dom = indicators.get("btc_dom")
    fg = indicators.get("fear_greed")
    cbbi = indicators.get("cbbi")
    if btc_dom is not None and fg is not None:
        rationale.append(f"BTC.D {btc_dom}%; Fear&Greed at {fg}.")
    if indicators.get("pi_cycle_flag"):
        rationale.append("Pi-Cycle flag set.")
    if indicators.get("trend_eth"):
        rationale.append(f"ETH trend: {indicators.get('trend_eth')}")

    for r in rationale[:4]:
        print("-", r)

    print("\nBefore -> After:")
    for k in ["BTC", "ETH", "ALTS"]:
        b = prev_weights.get(k, 0.0)
        a = target.get(k, 0.0)
        print(f"{k}: {b:.2f} -> {a:.2f}")

    print("\nActions:", printable_change(prev_weights, target))
    print("Charts:", before_path, after_path)

    print("Gating:", send, reason)

    # If gating says send and user requested --send (not dry-run), perform the send.
    if send and args.send:
        # Compose email and attachments (HTML fallback still available)
        from notify.emailer import compose_email
        subject, html_body, attachments = compose_email(prev_weights, target, indicators)

        sg_key = os.getenv("SENDGRID_API_KEY")
        template_id = os.getenv("SENDGRID_TEMPLATE_ID")
        # Print runtime report (no secrets)
        print(f"SendGrid? {bool(sg_key)}; Template? {bool(template_id)}; SMTP? {all(os.getenv(k) for k in ['SMTP_HOST','SMTP_PORT','SMTP_USER','SMTP_PASS','SMTP_FROM'])}; Gating: {send} ({reason})")

        if sg_key and template_id:
            # Build dynamic template data and send via template API; fail fast on errors
            from notify.sendgrid_payload import build_dynamic_template_data
            dynamic = build_dynamic_template_data(prev_weights, target, indicators)
            print("[SENDGRID TEMPLATE] Using template_id and dynamic data")
            try:
                from importlib import import_module
                sg = import_module("elon_mailer_sendgrid")
                sg.send_via_template(
                    template_id,
                    dynamic,
                    attachments,
                    os.getenv("ELON_TO_EMAIL", "barryaburnett@gmail.com"),
                    os.getenv("ELON_FROM_EMAIL"),
                    os.getenv("ELON_FROM_NAME"),
                    sg_key,
                )
                new_state = {"weights": target, "indicators": indicators, "sent_at": now_utc.isoformat()}
                write_last_sent(new_state)
            except Exception as exc:
                print("SendGrid send failed:", repr(exc))
                raise SystemExit(1)

        elif sg_key and not template_id:
            # API key present but no template: fallback to raw HTML send_via_sendgrid
            print("[SENDGRID RAW HTML] Sending raw HTML via SendGrid")
            try:
                from importlib import import_module
                sg = import_module("elon_mailer_sendgrid")
                sg.send_via_sendgrid(
                    subject,
                    html_body,
                    attachments,
                    os.getenv("ELON_TO_EMAIL", "barryaburnett@gmail.com"),
                    os.getenv("ELON_FROM_EMAIL"),
                    os.getenv("ELON_FROM_NAME"),
                    sg_key,
                )
                new_state = {"weights": target, "indicators": indicators, "sent_at": now_utc.isoformat()}
                write_last_sent(new_state)
            except Exception as exc:
                print("SendGrid send failed:", repr(exc))
                raise SystemExit(1)

        else:
            # No SendGrid API key: require SMTP vars and use SMTP
            smtp_keys = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM"]
            missing = [k for k in smtp_keys if not os.getenv(k)]
            if missing:
                print("SMTP_* vars are missing:", missing)
                raise SystemExit(2)
            print("[SMTP] Sending via SMTP")
            from notify.emailer import send_email
            send_email(subject, html_body, attachments, os.getenv("ELON_TO_EMAIL", "barryaburnett@gmail.com"))
            new_state = {"weights": target, "indicators": indicators, "sent_at": now_utc.isoformat()}
            write_last_sent(new_state)
    else:
        # Not sending (either gating prevented it, or --send not provided, or dry-run)
        if send and not args.send:
            print("Gating approved a send but --send not provided; run with --send to actually send")
        # For dry-run or not sending, still update state only when forced
        if args.dry_run:
            # simulate write on dry-run when send would have occurred
            if send:
                new_state = {"weights": target, "indicators": indicators, "sent_at": now_utc.isoformat()}
                write_last_sent(new_state)

    # Log run and source errors (if any)
    src_errs = indicators.get("source_errors") or []
    log_run(f"dry-run: send={send} reason={reason} saved_indicators={bool(args.save_indicators)} charts={before_path},{after_path} src_errors={src_errs}")


if __name__ == "__main__":
    main()
