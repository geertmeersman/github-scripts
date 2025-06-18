import os
import requests
from report_utils import wrap_html_report
from notify_utils import send_email_report

# === ENVIRONMENT VARIABLES ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USER = os.getenv("GITHUB_USER")

REQUESTS_TIMEOUT = 10

if not all([GITHUB_USER, GITHUB_TOKEN]):
    raise ValueError("❌ Missing one or more required environment variables.")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "github-scripts-bot"
}

def search_issues(query):
    url = f"https://api.github.com/search/issues?q={query}&per_page=100"
    response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
    response.raise_for_status()
    return response.json().get("items", [])

def format_labels(labels):
    if not labels:
        return "None"
    return ", ".join(label["name"] for label in labels)

def print_to_console(issue_data):
    for section, issues in issue_data.items():
        if not issues:
            continue  # Skip empty categories
        print(f"\n🔹 {section} ({len(issues)})")
        for issue in issues:
            repo = issue["repository_url"].split("/")[-1]
            labels = format_labels(issue.get("labels", []))
            comments = issue.get("comments", 0)
            print(f"  - #{issue['number']} {issue['title']} [{repo}]")
            print(f"    Labels: {labels} | Comments: {comments}")
            print(f"    {issue['html_url']} (by {issue['user']['login']})")

def generate_html_report(issue_data):
    html = ""
    for section, issues in issue_data.items():
        if not issues:
            continue  # Skip empty categories
        html += f"""
        <h3 style="border-bottom: 1px solid #eee; padding-bottom: 4px;">{section} ({len(issues)})</h3>
        """
        html += "<ul style='padding-left: 20px;'>"
        for issue in issues:
            repo = issue['repository_url'].split('/')[-1]
            labels = format_labels(issue.get("labels", []))
            comments = issue.get("comments", 0)
            html += f"""
            <li style="margin-bottom: 12px;">
              <a href="{issue['html_url']}" style="color: #0366d6; text-decoration: none;">
                #{issue['number']} {issue['title']}
              </a>
              <div style="font-size: 12px; color: #555;">
                in <strong>{repo}</strong> by <em>{issue['user']['login']}</em><br/>
                Labels: <em>{labels}</em> | Comments: <strong>{comments}</strong>
              </div>
            </li>
            """
        html += "</ul>"

    # If after skipping empty categories, html is empty, add a fallback message
    if not html.strip():
        html = "<p style='color: #999;'>No open issues found.</p>"

    return wrap_html_report(
        content_html=html,
        title="GitHub Issue Report",
        github_user=GITHUB_USER
    )

def group_issues_by_repo_owner(issue_results):
    grouped = {
        "Your Repositories": {},
        "Other Repositories": {}
    }

    for category, issues in issue_results.items():
        for issue in issues:
            repo_url = issue["repository_url"]
            owner = repo_url.split("/")[4]
            key = "Your Repositories" if owner.lower() == GITHUB_USER.lower() else "Other Repositories"
            if category not in grouped[key]:
                grouped[key][category] = []
            grouped[key][category].append(issue)

    # Remove empty categories here to avoid printing them later
    for key in grouped:
        grouped[key] = {cat: iss for cat, iss in grouped[key].items() if iss}

    return grouped

def main():
    print(f"📡 Fetching open issues for {GITHUB_USER}...\n")

    categories = {
        "Created by you": f"is:issue is:open author:{GITHUB_USER}",
        "Assigned to you": f"is:issue is:open assignee:{GITHUB_USER}",
        "Mentioning you": f"is:issue is:open mentions:{GITHUB_USER}"
    }

    issue_results = {name: search_issues(query) for name, query in categories.items()}

    grouped_issues = group_issues_by_repo_owner(issue_results)

    # Remove empty repo groups (if no categories left)
    grouped_issues = {k: v for k, v in grouped_issues.items() if v}

    total_issue_count = sum(
        len(issues)
        for repo_group in grouped_issues.values()
        for issues in repo_group.values()
    )
    if total_issue_count == 0:
        print("📭 No open issues found — skipping email report.")
        return

    for repo_group_name, repo_group in grouped_issues.items():
        print(f"\n=== {repo_group_name} ===")
        print_to_console(repo_group)

    html = ""
    for repo_group_name, repo_group in grouped_issues.items():
        html += f"<h2 style='border-bottom: 2px solid #444;'>{repo_group_name}</h2>"
        html += generate_html_report(repo_group)

    subject = f"GitHub Issue Report for {GITHUB_USER}"
    send_email_report(subject, html)

if __name__ == "__main__":
    main()
