#!/usr/bin/env python3
"""Rank Markdown deadlines by urgency. Standard library only.

Line format: - YYYY-MM-DD | Title | 6h   (the effort column is optional)
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

LINE_RE = re.compile(r"^\s*[-*]\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+?)\s*(?:\|\s*(\d+(?:\.\d+)?)\s*h\s*)?$")
# Assume about this many focused hours are available per day.
HOURS_PER_DAY = 3.0
DEFAULT_EFFORT = 2.0


def parse(text: str) -> tuple[list[dict], list[str]]:
    items, skipped = [], []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        match = LINE_RE.match(raw)
        try:
            items.append({"due": date.fromisoformat(match.group(1)), "title": match.group(2),
                          "effort": float(match.group(3) or DEFAULT_EFFORT)})
        except (AttributeError, ValueError):
            skipped.append(raw.strip())
    return items, skipped


def assess(item: dict, today: date) -> dict:
    days_left = (item["due"] - today).days
    days_needed = item["effort"] / HOURS_PER_DAY
    if days_left < 0:
        status = "OVERDUE"
    elif days_left < days_needed or days_left <= 1:
        status = "AT RISK"
    elif days_left <= 3:
        status = "SOON"
    else:
        status = "OK"
    return {"due": item["due"].isoformat(), "title": item["title"], "effortHours": item["effort"],
            "daysLeft": days_left, "status": status}


def rank(items: list[dict], today: date, days: int) -> list[dict]:
    assessed = [assess(i, today) for i in items]
    order = {"OVERDUE": 0, "AT RISK": 1, "SOON": 2, "OK": 3}
    return sorted((a for a in assessed if a["daysLeft"] <= days),
                  key=lambda a: (order[a["status"]], a["daysLeft"], -a["effortHours"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--days", type=int, default=14, help="look-ahead window")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.file.exists():
        print(f"No deadlines file at {args.file}", file=sys.stderr)
        return 1
    items, skipped = parse(args.file.read_text(encoding="utf-8"))
    ranked = rank(items, args.today, args.days)
    if args.json:
        print(json.dumps({"deadlines": ranked, "unparsable": skipped}, indent=2))
        return 0
    for entry in ranked:
        print(f"{entry['status']:8} {entry['due']} ({entry['daysLeft']:+d}d, ~{entry['effortHours']:g}h) {entry['title']}")
    for line in skipped:
        print(f"UNPARSABLE: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
