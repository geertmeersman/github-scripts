import os
import requests
import time
import argparse
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
merged_prs = []
processed_prs = []


def get_repos():
    """
    Fetches the list of repositories the authenticated user has push access to.

    Returns:
        list[str]: List of repository full names (e.g., 'user/repo').
    """
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


def get_user_prs(repo, target_user):
    """
    Fetches open pull requests from a given repository created by a specific user.

    Args:
        repo (str): Full repository name (e.g., 'user/repo').
        target_user (str): GitHub username or bot account (e.g., 'dependabot[bot]').

    Returns:
        list[dict]: List of pull request dictionaries.
    """
    url = f"https://api.github.com/repos/{repo}/pulls?state=open"
    response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
    if response.status_code != 200:
        print(f"❌ Failed to fetch PRs for {repo}")
        return []
    return [pr for pr in response.json() if pr['user']['login'] == target_user]


def merge_pr(repo, pr, target_user):
    """
    Attempts to auto-merge a pull request if it is mergeable.

    Args:
        repo (str): Full repository name.
        pr (dict): Pull request data.
        target_user (str): Username used in commit title.

    Side Effects:
        Updates global merged_prs or unmerged_prs lists with the outcome.
    """
    pr_number = pr['number']
    pr_title = pr['title']
    pr_url = pr['html_url']
    print(f"🔄 Attempting to merge PR #{pr_number} - {pr_title} in {repo}")

    details_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    details = requests.get(details_url, headers=HEADERS, timeout=REQUESTS_TIMEOUT).json()

    if details.get('mergeable') is not True:
        reason = details.get('mergeable_state', 'unknown')
        reason_msg = "Merge conflict" if reason == "dirty" else f"Not mergeable ({reason})"
        print(f"⏭️ PR #{pr_number} is not mergeable: {reason_msg}")
        unmerged_prs.append((repo, pr_number, pr_title, pr_url, reason_msg))
        return

    merge_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/merge"
    data = {
        "merge_method": MERGE_METHOD,
        "commit_title": f"Auto-merge PR #{pr_number} from {target_user}"
    }
    response = requests.put(merge_url, headers=HEADERS, json=data, timeout=REQUESTS_TIMEOUT)

    if response.status_code == 200:
        print(f"✅ Merged PR #{pr_number} - {pr_title} in {repo}")
        merged_prs.append((repo, pr_number, pr_title, pr_url))
    else:
        error = response.json().get('message', 'Unknown error')
        print(f"❌ Failed to merge PR #{pr_number} - {pr_title} in {repo}: {error}")
        unmerged_prs.append((repo, pr_number, pr_title, pr_url, error))


def build_and_send_email(user):
    """
    Builds an HTML report and sends it via email for merged/unmerged PRs.

    Args:
        user (str): GitHub username the report is for.
    """
    subject = f"[Auto-Merge] {len(unmerged_prs)} unmerged, {len(merged_prs)} merged for {user}"

    body = ""
    if merged_prs:
        body += "<h3>Merged PRs</h3><ul>"
        for repo, pr_number, title, url in merged_prs:
            body += f'<li><a href="{url}">{repo}#{pr_number}</a>: {title}</li>'
        body += "</ul>"

    if unmerged_prs:
        body += "<h3>Unmerged PRs</h3><ul>"
        for repo, pr_number, title, url, reason in unmerged_prs:
            body += f'<li><a href="{url}">{repo}#{pr_number}</a>: {title} — {reason}</li>'
        body += "</ul>"

    if not merged_prs and not unmerged_prs:
        body = f"<p>All PRs from {user} were merged successfully! 🎉</p>"

    html_report = wrap_html_report(
        content_html=body,
        title="Auto-Merge Report",
        github_user=GITHUB_USER
    )
    send_email_report(subject, html_report)


def build_and_send_telegram(user):
    """
    Sends a summary of merged/unmerged PRs via Telegram.

    Args:
        user (str): GitHub username the report is for.
    """
    merged = "\n".join([f"✅ [{repo}#{num}]({url}) — {title}" for repo, num, title, url in merged_prs])
    unmerged = "\n".join([f"⚠️ [{repo}#{num}]({url}) — {title} — {reason}" for repo, num, title, url, reason in unmerged_prs])

    if not merged_prs and not unmerged_prs:
        text = f"✅ *[Auto-Merge]* All PRs from `{user}` merged\nNothing left to review."
    else:
        text = f"*[Auto-Merge]* Report for `{user}`:\n"
        if merged:
            text += f"\n*Merged PRs:*\n{merged}"
        if unmerged:
            text += f"\n\n*Unmerged PRs:*\n{unmerged}"

    send_telegram_report(text)


def main():
    """
    Main entry point for auto-merging pull requests for a specified user.

    Parses CLI arguments, fetches repositories and PRs, and merges auto-mergeable PRs.
    Sends a report via email and Telegram.
    """
    parser = argparse.ArgumentParser(description="Auto-merge PRs for a specified user (default: dependabot[bot])")
    parser.add_argument("--user", default="dependabot[bot]", help="GitHub username to auto-merge PRs for")
    args = parser.parse_args()
    target_user = args.user

    repos = get_repos()
    print(f"📦 Found {len(repos)} repositories")
    for repo in repos:
        prs = get_user_prs(repo, target_user)
        if prs:
            processed_prs.extend(prs)
        for pr in prs:
            merge_pr(repo, pr, target_user)
            time.sleep(1)

    if processed_prs:
        build_and_send_email(target_user)
        build_and_send_telegram(target_user)
    else:
        print(f"📭 No PRs from {target_user} found — skipping notifications.")


if __name__ == '__main__':
    main()
