#!/usr/bin/env python3
"""Run scheduled automation jobs without Celery (for GitHub Actions)."""

from __future__ import annotations

import argparse
import json
import sys

from app.workers import tasks


JOBS = {
    "discovery": tasks.daily_outreach_task,
    "send": tasks.hourly_outreach_send_task,
    "sheets-sync": tasks.sheets_sync_task,
    "gmail-reconcile": tasks.gmail_reconcile_task,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LinkedIn Manager scheduled jobs")
    parser.add_argument("job", choices=sorted(JOBS.keys()))
    args = parser.parse_args()
    result = JOBS[args.job]()
    print(json.dumps(result, default=str))
    if isinstance(result, dict) and result.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
