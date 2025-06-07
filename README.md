
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



# Dependabot Auto-Merge & Scripts Dashboard

Automate merging Dependabot pull requests across multiple GitHub repositories with notifications by email and Telegram.  
Includes a lightweight Flask web dashboard for manual script execution and status monitoring.

---

## Features

- Auto-merge Dependabot PRs in multiple repos
- Email and Telegram notifications with PR info
- Runs as a scheduled cron job inside Docker
- Web UI to manually run scripts and view their output
- Supports multiple scripts with descriptions
- Execution status indicators in UI
- Configurable web interface port

---

## Getting Started

### Prerequisites

- Docker installed (recommended)
- GitHub Personal Access Token with repo permissions
- SMTP server for sending emails
- Telegram Bot ID and Chat ID for notifications (optional)

### Environment Variables

Set the following environment variables (e.g., in `.env` file or Docker environment):

| Variable          | Description                                 | Required  |
|-------------------|---------------------------------------------|-----------|
| `GITHUB_TOKEN`    | GitHub API token with repo permissions      | Yes       |
| `EMAIL_TO`        | Recipient email address                     | Yes       |
| `EMAIL_FROM`      | Sender email address                        | Yes       |
| `SMTP_HOST`       | SMTP server hostname                        | Yes       |
| `SMTP_PORT`       | SMTP server port (e.g., 587)                | Yes       |
| `SMTP_USER`       | SMTP username                               | Yes       |
| `SMTP_PWD`        | SMTP password                               | Yes       |
| `TELEGRAM_BOT_ID` | Telegram bot token (optional)               | No        |
| `TELEGRAM_CHAT_ID`| Telegram chat ID to send messages (optional)| No        |
| `WEB_PORT`        | Port for web interface (default: 80)        | No        |

---

## Usage

### Build Docker Image

```bash
docker build -t github-scripts .
```

### Run Container

```bash
docker run -p 80:80 github-scripts
```

- The web UI will be available at `http://localhost:80`
- The auto-merge script runs as a scheduled cron job inside the container
- Use the web UI to manually trigger scripts and view output/status

---

## Web Interface

- Navigate to `/` (e.g., `http://localhost:80`)
- View available scripts with descriptions and execution status
- Click **Run Script** to start a script asynchronously
- Refresh page to see updated status and output

---

## Security Considerations

- Consider adding authentication to the web interface if exposed publicly
- Keep your GitHub token and SMTP credentials secure
- Limit network access to the container if possible

---

## Troubleshooting

- Check container logs for errors:
  ```bash
  docker logs <container_id>
  ```
- Verify environment variables are correctly set
- Make sure SMTP credentials and Telegram bot info are valid
- Ensure GitHub token has appropriate repo permissions

---

## License

MIT License

---

