#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         CRONTAB HUMANIZER – Docker Startup Utility          ║
╠══════════════════════════════════════════════════════════════╣
║ Reads cron expressions from /etc/cron.d/color-printer and   ║
║ uses cron-descriptor to generate human-readable schedules.  ║
║                                                              ║
║ Example:                                                     ║
║   0 11 * * 5   →   At 11:00 AM, only on Friday               ║
║                                                              ║
║ Author: Geert Meersman 🚀                                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import re

from cron_descriptor import get_description

print("📆   Scheduled Cron Jobs:\n")

with open("/etc/cron.d/github_scripts") as file:
    for line in file:
        line = line.strip()

        if not line or line.startswith("#") or "=" in line:
            continue

        match = re.match(r"^(\S+\s+\S+\s+\S+\s+\S+\s+\S+)", line)
        if match:
            cron_expr = match.group(1)
            try:
                human = get_description(cron_expr)
                print(f"🕒   {cron_expr} → {human}")
            except Exception as e:  # noqa: BLE001
                print(f"⚠️   Failed to parse: {cron_expr} ({e})")
        else:
            print(f"⚠️   Skipped non-cron line: {line}")
