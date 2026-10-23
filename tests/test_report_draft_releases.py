import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "github"))

import report_draft_releases


class TestGetRepos:
    def test_returns_repos_with_push_access(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            [{"full_name": "user/repo1", "permissions": {"push": True}}],
            [{"full_name": "user/repo2", "permissions": {"push": False}}],
            [],
        ]
        with patch("requests.get", return_value=mock_response):
            result = report_draft_releases.get_repos()
        assert result == ["user/repo1"]


class TestGetDraftRelease:
    def test_returns_draft_release(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "draft": True,
                "tag_name": "v1.0.0",
                "html_url": "https://github.com/user/repo/releases/1",
                "body": "## Changes",
            },
            {"draft": False, "tag_name": "v0.9.0", "html_url": "https://github.com/user/repo/releases/2", "body": ""},
        ]
        with patch("requests.get", return_value=mock_response):
            result = report_draft_releases.get_draft_release("user/repo")
        assert result["tag_name"] == "v1.0.0"

    def test_returns_none_when_no_draft(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"draft": False, "tag_name": "v1.0.0", "html_url": "https://github.com/user/repo/releases/1", "body": ""},
        ]
        with patch("requests.get", return_value=mock_response):
            result = report_draft_releases.get_draft_release("user/repo")
        assert result is None

    def test_returns_none_on_failed_request(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("requests.get", return_value=mock_response):
            result = report_draft_releases.get_draft_release("user/repo")
        assert result is None


class TestGetReleaseWorkflow:
    def test_finds_release_yml(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("requests.get", return_value=mock_response):
            result = report_draft_releases.get_release_workflow("user/repo")
        assert result == "release.yml"

    def test_falls_back_to_docker_build(self):
        responses = [MagicMock(status_code=404), MagicMock(status_code=200)]
        with patch("requests.get", side_effect=responses):
            result = report_draft_releases.get_release_workflow("user/repo")
        assert result == "docker-build.yml"

    def test_returns_none_when_no_workflow(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("requests.get", return_value=mock_response):
            result = report_draft_releases.get_release_workflow("user/repo")
        assert result is None


class TestGenerateHtmlReport:
    def setup_method(self):
        report_draft_releases.GITHUB_USER = "testuser"

    def test_contains_repo_name(self):
        release = {"html_url": "https://github.com/user/repo/releases/1", "tag_name": "v1.0.0", "body": "## Changes"}
        result = report_draft_releases.generate_html_report([("user/repo", release, "release.yml")])
        assert "repo" in result

    def test_contains_trigger_link(self):
        release = {"html_url": "https://github.com/user/repo/releases/1", "tag_name": "v1.0.0", "body": ""}
        result = report_draft_releases.generate_html_report([("user/repo", release, "release.yml")])
        assert "Trigger release" in result

    def test_no_trigger_link_when_no_workflow(self):
        release = {"html_url": "https://github.com/user/repo/releases/1", "tag_name": "v1.0.0", "body": ""}
        result = report_draft_releases.generate_html_report([("user/repo", release, None)])
        assert "Trigger release" not in result

    def test_handles_empty_body(self):
        release = {"html_url": "https://github.com/user/repo/releases/1", "tag_name": "v1.0.0", "body": ""}
        result = report_draft_releases.generate_html_report([("user/repo", release, None)])
        assert "No release notes yet" in result
