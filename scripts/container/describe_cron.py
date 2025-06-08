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

from cron_descriptor import get_description
import re

print("📆   Scheduled Cron Jobs:\n")

with open("/etc/cron.d/github_scripts", "r") as file:
    for line in file:
        # Remove leading/trailing spaces
        line = line.strip()

        # Skip comments, env vars, or empty lines
        if not line or line.startswith("#") or "=" in line:
            continue

        # Match first 5 fields (cron expression)
        match = re.match(r"^(\S+\s+\S+\s+\S+\s+\S+\s+\S+)", line)
        if match:
            cron_expr = match.group(1)
            try:
                human = get_description(cron_expr)
                print(f"🕒   {cron_expr} → {human}")
            except Exception as e:
                print(f"⚠️   Failed to parse: {cron_expr} ({e})")
        else:
            print(f"⚠️   Skipped non-cron line: {line}")
