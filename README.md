
[![maintainer](https://img.shields.io/badge/maintainer-Geert%20Meersman-green?style=for-the-badge&logo=github)](https://github.com/geertmeersman)
[![buyme_coffee](https://img.shields.io/badge/Buy%20me%20an%20Omer-donate-yellow?style=for-the-badge&logo=buymeacoffee)](https://www.buymeacoffee.com/geertmeersman)
[![MIT License](https://img.shields.io/github/license/geertmeersman/github-scripts?style=for-the-badge)](https://github.com/geertmeersman/github-scripts/blob/main/LICENSE)

[![GitHub issues](https://img.shields.io/github/issues/geertmeersman/github-scripts)](https://github.com/geertmeersman/github-scripts/issues)
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/geertmeersman/github-scripts.svg)](http://isitmaintained.com/project/geertmeersman/github-scripts)
[![Percentage of issues still open](http://isitmaintained.com/badge/open/geertmeersman/github-scripts.svg)](http://isitmaintained.com/project/geertmeersman/github-scripts)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](https://github.com/geertmeersman/github-scripts/pulls)

[![github release](https://img.shields.io/github/v/release/geertmeersman/github-scripts?logo=github)](https://github.com/geertmeersman/github-scripts/releases)
[![github release date](https://img.shields.io/github/release-date/geertmeersman/github-scripts)](https://github.com/geertmeersman/github-scripts/releases)
[![github last-commit](https://img.shields.io/github/last-commit/geertmeersman/github-scripts)](https://github.com/geertmeersman/github-scripts/commits)
[![github contributors](https://img.shields.io/github/contributors/geertmeersman/github-scripts)](https://github.com/geertmeersman/github-scripts/graphs/contributors)
[![github commit activity](https://img.shields.io/github/commit-activity/y/geertmeersman/github-scripts?logo=github)](https://github.com/geertmeersman/github-scripts/commits/main)

![Docker Pulls](https://img.shields.io/docker/pulls/geertmeersman/github-scripts)
![Docker Image Version](https://img.shields.io/docker/v/geertmeersman/github-scripts?label=docker%20image%20version)



# 🔄 GitHub Scripts Dashboard

A Dockerized automation suite to manage GitHub workflows like auto-merging Dependabot PRs and sending daily PR reports — complete with a web interface, cron integration, and notifications.

---

## 📆 Overview

This container:

* 🧠 Automatically **merges Dependabot PRs**
* 📧 **Emails you** a daily **PR report** (PRs authored/assigned/mentioning you)
* 🖥️ Exposes a **Flask dashboard** (on port 80) to manually trigger/monitor scripts
* 🔁 Runs on **cron** internally (02:00 and 06:00)
* 📨 Sends **email + Telegram** notifications
* 📌 Logs all activity to `/var/log/github-scripts/`

Built and maintained by [Geert Meersman](https://github.com/gmeersman)

---

## 🧠 Features

| Feature                    | Description                                            |
| -------------------------- | ------------------------------------------------------ |
| 🔁 Auto-Merge              | Merges eligible Dependabot PRs using GitHub API        |
| 📧 PR Report Emails        | Sends daily HTML summary of PRs authored/assigned/etc. |
| 🖥️ Web UI                 | Run and view scripts via browser (port 80)             |
| 🥐 Cron-Based Execution    | Auto-runs at 2:00 and 6:00 UTC                         |
| 🔔 Email & Telegram Alerts | Optional notifications on success/failure              |
| ❤️ Lightweight Container   | Based on `python:3.11-slim`                            |

---

## 📂 File Structure

```
/scripts/github/
├── auto_merge_dependabot.py     # Script: merge dependabot PRs
├── report_open_prs.py           # Script: send PR report
├── notify_utils.py              # Utilities: Email & Telegram
├── report_utils.py              # Utilities: HTML report wrapper
├── scripts.json                 # Metadata for dashboard

/scripts/container/
├── cron_wrapper.py              # Wrapper: logs script + error output
├── describe_cron.py             # Describes cron jobs at startup
├── healthcheck.sh               # Healthcheck used by Docker

/web/
└── web_interface.py             # Flask dashboard (port 80)

/cron/
└── cronjob                      # All cron job entries

/docker-compose/
└── compose.yml                  # Docker compose config

entrypoint.sh                    # Starts cron + Flask via Gunicorn
Dockerfile
VERSION
```

---

## ⚙️ Environment Variables (`.env`)

```env
# Web
WEB_PORT=80

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

# Volume path
LOG_VOLUME=<path-for-log-mount>
```

---

## 🚪 Running It

### 🔧 Build Image

```bash
docker build -t github-scripts .
```

### 🚀 Run Container

```bash
docker run -d \
  --env-file .env \
  --name github-scripts \
  -p 80:80 \
  github-scripts
```

The dashboard will be available at: [http://localhost](http://localhost)

---

## ⏰ Cron Schedule (Inside Container)

| Time (UTC) | Script                  | Log File                                                 |
| ---------- | ----------------------- | -------------------------------------------------------- |
| 02:00      | `auto_merge_dependabot` | `/var/log/github-scripts/auto_merge_dependabot_cron.log` |
| 06:00      | `report_open_prs`       | `/var/log/github-scripts/report_open_prs_cron.log`       |

Each job is executed through `cron_wrapper.py`, which logs stdout and stderr.

---

## 📨 Notifications

* **Email**: Sent using SMTP config (see `.env`)
* **Telegram**: Optional webhook alert for job success/failure

If credentials are missing, notification modules gracefully skip execution.

---

## ♻️ Entrypoint Behavior

On container start:

1. ✅ Environment is dumped to `/env.sh`
2. ⏰ Cron daemon starts
3. 📜 Cron jobs are described via `describe_cron.py`
4. 🌐 Flask app is launched on port `80` using Gunicorn

Logs and errors are automatically routed for cron jobs and can be inspected using:

```bash
docker exec -it github-scripts tail -n 100 /var/log/github-scripts/*.log
```

---

## ✅ Healthcheck

Docker health check runs via `/healthcheck.sh`, which confirms the Flask UI is up.

```bash
curl http://localhost/health
```

---

## 👤 Author

Geert Meersman — [@gmeersman](https://github.com/gmeersman)

MIT License
