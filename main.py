"""
CLI entrypoint for Elon Rotation Bot.
Handles indicator loading, allocation, gating, email composition, logging, and flags.
"""
import argparse
from datetime import datetime, timezone
# ...
now = datetime.now(timezone.utc)

from indicators.loader import load_indicators
from rotation.allocator import allocate
# ...existing code...

def main():
    parser = argparse.ArgumentParser(description="Elon Rotation Bot")
    parser.add_argument("--dry-run", action="store_true", help="No email sent")
    parser.add_argument("--force", action="store_true", help="Bypass gating")
    parser.add_argument("--save-indicators", type=str, help="Save indicators to path.json")
    args = parser.parse_args()

    now = datetime.utcnow()
    indicators = load_indicators(now)
    target = allocate(indicators)
    # TODO: Implement gating, email, logging

if __name__ == "__main__":
    main()
