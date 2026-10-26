import os

import requests
from notify_utils import send_email_report
from report_utils import wrap_html_report

GITHUB_USER = os.getenv("GITHUB_USER")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

REQUESTS_TIMEOUT = 10

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def get_repos():
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/user/repos?per_page=100&page={page}"
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        if response.status_code != 200:
            break
        data = response.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return [r["full_name"] for r in repos if r["permissions"]["push"]]


def get_draft_release(repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
    if response.status_code != 200:
        return None
    for release in response.json():
        if release.get("draft"):
            return release
    return None


def get_release_workflow(repo):
    """Find the release/docker-build workflow that can be triggered."""
    for workflow_name in ["release.yml", "docker-build.yml"]:
        url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_name}"
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        if response.status_code == 200:
            return workflow_name
    return None


def markdown_to_html(text, repo):
    """Convert markdown to HTML using the GitHub API."""
    response = requests.post(
        "https://api.github.com/markdown",
        headers=HEADERS,
        json={"text": text, "mode": "gfm", "context": repo},
        timeout=REQUESTS_TIMEOUT,
    )
    if response.status_code == 200:
        return response.text
    return text.replace("\n", "<br>")


def generate_html_report(draft_releases):
    html = ""
    for repo, release, workflow in draft_releases:
        repo_name = repo.split("/")[-1]
        release_url = release["html_url"]
        tag = release.get("tag_name", "?")
        body = release.get("body", "").strip()
        if body:
            body_html = markdown_to_html(body, repo)
        else:
            body_html = "<em>No release notes yet.</em>"

        trigger_html = ""
        if workflow:
            trigger_url = f"https://github.com/{repo}/actions/workflows/{workflow}"
            trigger_html = f"""
            <div style="margin-top: 8px;">
              <a href="{trigger_url}" style="
                display: inline-block;
                padding: 6px 14px;
                background-color: #2ea44f;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;">
                🚀 Trigger release for {repo_name}
              </a>
            </div>"""

        html += f"""
        <div style="margin-bottom: 32px; padding: 16px; border: 1px solid #e1e4e8; border-radius: 8px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <h3 style="margin: 0;">
              <a href="https://github.com/{repo}" style="color: #0366d6; text-decoration: none;">
                {repo_name}
              </a>
            </h3>
            <span style="background: #f1f8ff; color: #0366d6; border: 1px solid #c8e1ff;
                         padding: 2px 8px; border-radius: 12px; font-size: 12px;">
              {tag}
            </span>
          </div>
          <div style="font-size: 13px; color: #586069; margin-bottom: 10px;">
            <a href="{release_url}" style="color: #586069;">📝 View draft release</a>
          </div>
          <div style="background: #f6f8fa; padding: 12px; border-radius: 6px;
                      font-size: 13px; color: #24292e; line-height: 1.6;">
            {body_html}
          </div>
          {trigger_html}
        </div>
        """

    return wrap_html_report(
        content_html=html,
        title="Draft Releases Report",
        github_user=GITHUB_USER,
    )


def main():
    if not all([GITHUB_USER, GITHUB_TOKEN]):
        raise ValueError("❌ Missing one or more required environment variables.")

    print(f"📡 Fetching repositories for {GITHUB_USER}...")
    repos = get_repos()
    print(f"📦 Found {len(repos)} repositories")

    draft_releases = []
    for repo in repos:
        release = get_draft_release(repo)
        if release:
            workflow = get_release_workflow(repo)
            draft_releases.append((repo, release, workflow))
            print(f"  📝 {repo}: draft {release.get('tag_name', '?')}")

    if not draft_releases:
        print("📭 No draft releases found — skipping email report.")
        return

    print(f"\n📬 Sending report for {len(draft_releases)} draft release(s)...")
    html_report = generate_html_report(draft_releases)
    subject = f"📝 {len(draft_releases)} draft release(s) pending — {GITHUB_USER}"
    send_email_report(subject, html_report)


if __name__ == "__main__":
    main()
