#!/bin/bash
set -e

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}


cat << "EOF"
 _____                _    ___  ___                                         
|  __ \              | |   |  \/  |                                         
| |  \/ ___  ___ _ __| |_  | .  . | ___  ___ _ __ ___ _ __ ___   __ _ _ __  
| | __ / _ \/ _ \ '__| __| | |\/| |/ _ \/ _ \ '__/ __| '_ ` _ \ / _` | '_ \ 
| |_\ \  __/  __/ |  | |_  | |  | |  __/  __/ |  \__ \ | | | | | (_| | | | |
 \____/\___|\___|_|   \__| \_|  |_/\___|\___|_|  |___/_| |_| |_|\__,_|_| |_|
                                                                            

Github Scripts Docker Container
by Geert Meersman
===========================================

This container automates merging Dependabot pull requests across multiple GitHub repositories with notifications by email and Telegram.
Includes a lightweight Flask web dashboard for manual script execution and status monitoring.
---------------------------------------------------------------------------------------------------------


EOF

# Dump selected environment variables with quoting
{
  printenv | grep -E '^(WEB_PORT|GITHUB_TOKEN|GITHUB_USER|MERGE_METHOD|PRINTER_URI|PRINTER_NAME|SMTP_USER|SMTP_PWD|SMTP_SERVER|SMTP_PORT|EMAIL_FROM|EMAIL_TO|TELEGRAM_BOT_ID|TELEGRAM_CHAT_ID)=' | \
    while IFS='=' read -r key value; do
      echo "export ${key}=\"${value//\"/\\\"}\""
    done
} > /env.sh
chmod +x /env.sh


# Start cron
log "[INFO] Starting cron..."
cron
log "[INFO] Describing cron jobs..."
python3 /home/describe_cron.py

# Start Flask app
WEB_PORT="${WEB_PORT:-80}"
echo "[INFO] Starting Flask app on port $WEB_PORT with Gunicorn..."
exec gunicorn --chdir /home --bind 0.0.0.0:$WEB_PORT web_interface:app

# Optional: keep container running to troubleshoot, or exit
tail -f /dev/null
