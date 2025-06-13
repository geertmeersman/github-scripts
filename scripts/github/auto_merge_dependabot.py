import os
import requests
import time
from report_utils import wrap_html_report
from notify_utils import send_email_report, send_telegram_report

# === CONFIG ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USER = os.getenv("GITHUB_USER")
MERGE_METHOD = os.getenv("MERGE_METHOD", "squash")
REQUESTS_TIMEOUT = 10

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

unmerged_prs = []
processed_prs = []



def get_repos():
    repos = []
    page = 1
    while True:
        url = f'https://api.github.com/user/repos?per_page=100&page={page}'
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        if response.status_code != 200:
            print("❌ Failed to fetch repos")
            break
        data = response.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return [r['full_name'] for r in repos if r['permissions']['push']]


def get_dependabot_prs(repo):
    url = f"https://api.github.com/repos/{repo}/pulls?state=open"
    response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
    if response.status_code != 200:
        print(f"❌ Failed to fetch PRs for {repo}")
        return []
    return [pr for pr in response.json() if pr['user']['login'] == 'dependabot[bot]']


def merge_pr(repo, pr):
    pr_number = pr['number']
    pr_url = pr['html_url']
    print(f"🔄 Attempting to merge PR #{pr_number} in {repo}")

    details = requests.get(f"https://api.github.com/repos/{repo}/pulls/{pr_number}", headers=HEADERS, timeout=REQUESTS_TIMEOUT).json()
    if details.get('mergeable') is not True:
        print(f"⏭️ PR #{pr_number} is not mergeable yet")
        unmerged_prs.append((repo, pr_number, pr_url, "Not mergeable"))
        return

    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/merge"
    data = {
        "merge_method": MERGE_METHOD,
        "commit_title": f"Auto-merge PR #{pr_number} from Dependabot"
    }
    response = requests.put(url, headers=HEADERS, json=data, timeout=REQUESTS_TIMEOUT)
    if response.status_code == 200:
        print(f"✅ Merged PR #{pr_number} in {repo}")
    else:
        error = response.json().get('message', 'Unknown error')
        print(f"❌ Failed to merge PR #{pr_number} in {repo}: {error}")
        unmerged_prs.append((repo, pr_number, pr_url, error))


def build_and_send_email():
    subject = f"[Dependabot Auto-Merge] {len(unmerged_prs)} PR(s) not merged"
    if unmerged_prs:
        body = "<h3>Unmerged PRs</h3><ul>"
        for repo, pr_number, url, reason in unmerged_prs:
            body += f'<li><a href="{url}">{repo}#{pr_number}</a>: {reason}</li>'
        body += "</ul>"
    else:
        body = "<p>All Dependabot PRs were merged successfully! 🎉</p>"

    html_report = wrap_html_report(
        content_html=body,
        title="Dependabot Auto-Merge Report",
        github_user=GITHUB_USER
    )
    send_email_report(subject, html_report)


def build_and_send_telegram():
    if unmerged_prs:
        icon = "⚠️"
        status = f"{len(unmerged_prs)} PR(s) not merged"
        message = "\n".join([f"[{repo}#{num}]({url}) — {reason}" for repo, num, url, reason in unmerged_prs])
    else:
        icon = "✅"
        status = "All Dependabot PRs merged"
        message = "Nothing left to review."

    text = f"{icon} *[Dependabot Merge]* {status}\n{message}"
    send_telegram_report(text)


def main():
    repos = get_repos()
    print(f"📦 Found {len(repos)} repositories")
    for repo in repos:
        prs = get_dependabot_prs(repo)
        if prs:
            processed_prs.extend(prs)
        for pr in prs:
            merge_pr(repo, pr)
            time.sleep(1)

    if processed_prs:
        build_and_send_email()
        build_and_send_telegram()
    else:
        print("📭 No Dependabot PRs found — skipping notifications.")


if __name__ == '__main__':
    main()
