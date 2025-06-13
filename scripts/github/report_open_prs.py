import os
import requests
from report_utils import wrap_html_report
from notify_utils import send_email_report

# === ENVIRONMENT VARIABLES ===
GITHUB_USER = os.getenv("GITHUB_USER")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

REQUESTS_TIMEOUT = 10

if not all([GITHUB_USER, GITHUB_TOKEN]):
    raise ValueError("❌ Missing one or more required environment variables.")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def search_prs(query):
    url = f"https://api.github.com/search/issues?q={query}&per_page=100"
    response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
    response.raise_for_status()
    return response.json().get("items", [])

def print_to_console(pr_data):
    print(f"\n📄 GitHub PR Report for {GITHUB_USER}\n" + "-" * 40)
    for section, prs in pr_data.items():
        print(f"\n🔹 {section} ({len(prs)})")
        if not prs:
            print("  No open pull requests found.")
        for pr in prs:
            repo = pr["repository_url"].split("/")[-1]
            print(f"  - #{pr['number']} {pr['title']} [{repo}]")
            print(f"    {pr['html_url']} (by {pr['user']['login']})")

def generate_html_report(pr_data):
    html = ""
    for section, prs in pr_data.items():
        html += f"""
        <h3 style="border-bottom: 1px solid #eee; padding-bottom: 4px;">{section} ({len(prs)})</h3>
        """
        if not prs:
            html += "<p style='color: #999;'>No open pull requests found.</p>"
        else:
            html += "<ul style='padding-left: 20px;'>"
            for pr in prs:
                repo = pr['repository_url'].split('/')[-1]
                html += f"""
                <li style="margin-bottom: 8px;">
                  <a href="{pr['html_url']}" style="color: #0366d6; text-decoration: none;">
                    #{pr['number']} {pr['title']}
                  </a>
                  <div style="font-size: 12px; color: #555;">
                    in <strong>{repo}</strong> by <em>{pr['user']['login']}</em>
                  </div>
                </li>
                """
            html += "</ul>"

    return wrap_html_report(
        content_html=html,
        title="GitHub Pull Request Report",
        github_user=GITHUB_USER
    )

def main():
    print(f"📡 Fetching open pull requests for {GITHUB_USER}...\n")

    categories = {
        "Created by you": f"is:pr is:open author:{GITHUB_USER}",
        "Assigned to you": f"is:pr is:open assignee:{GITHUB_USER}",
        "Mentioning you": f"is:pr is:open mentions:{GITHUB_USER}",
        "Review requested from you": f"is:pr is:open review-requested:{GITHUB_USER}"
    }

    pr_results = {name: search_prs(query) for name, query in categories.items()}

    # Check if there's at least one PR
    total_pr_count = sum(len(prs) for prs in pr_results.values())
    if total_pr_count == 0:
        print("📭 No open PRs found — skipping email report.")
        return

    print_to_console(pr_results)
    html_report = generate_html_report(pr_results)

    subject = f"GitHub PR Report for {GITHUB_USER}"
    send_email_report(subject, html_report)

if __name__ == "__main__":
    main()
