# 🔄 GitHub Scripts Dashboard

A Dockerized automation suite to manage GitHub workflows like auto-merging Dependabot PRs and sending daily PR reports — complete with a web interface, cron integration, and notifications.

## Features

| Feature | Description |
|---------|-------------|
| 🔁 Auto-Merge | Merges eligible Dependabot PRs using GitHub API |
| 📧 PR Report Emails | Sends daily HTML summary of PRs authored/assigned/etc. |
| 🖥️ Web UI | Run and view scripts via browser (port 80) |
| 🥐 Cron-Based Execution | Auto-runs at 2:00 and 6:00 UTC |
| 🔔 Email & Telegram Alerts | Optional notifications on success/failure |
| ❤️ Lightweight Container | Based on `python:3.13-slim` — currently pinned to `3.13.18-slim` |

## Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `v1.2.3` | Specific release version |

## Quick start

```yaml
services:
  github-scripts:
    image: geertmeersman/github-scripts:latest
    container_name: github-scripts
    restart: unless-stopped
    env_file: .env
    ports:
      - "80:80"
```

## Environment variables

```env
# GitHub
GITHUB_USER=<your-github-user>
GITHUB_TOKEN=<your-token>
MERGE_METHOD=squash

# Email (optional)
SMTP_USER=<your-user>
SMTP_PWD=<your-password>
SMTP_SERVER=<smtp-server>
SMTP_PORT=587
EMAIL_FROM=<email-from>
EMAIL_TO=<email-to>

# Telegram (optional)
TELEGRAM_BOT_ID=<your-bot-id>
TELEGRAM_CHAT_ID=<your-chat-id>
```

## Base image

`python:3.13-slim` — currently pinned to `3.13.18-slim`

## Links

- 📖 [Full documentation & source code](https://github.com/geertmeersman/github-scripts)
- 🐛 [Report an issue](https://github.com/geertmeersman/github-scripts/issues)
- 📋 [Changelog](https://github.com/geertmeersman/github-scripts/releases)
- 📜 [License — MIT](https://github.com/geertmeersman/github-scripts/blob/main/LICENSE)
