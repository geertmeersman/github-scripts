import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "github"))

import auto_merge_prs


@pytest.fixture(autouse=True)
def clear_pr_lists():
    auto_merge_prs.merged_prs.clear()
    auto_merge_prs.unmerged_prs.clear()
    auto_merge_prs.processed_prs.clear()


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
            result = auto_merge_prs.get_repos()
        assert result == ["user/repo1"]

    def test_stops_on_failed_request(self):
        mock_response = MagicMock()
        mock_response.status_code = 403
        with patch("requests.get", return_value=mock_response):
            result = auto_merge_prs.get_repos()
        assert result == []


class TestGetUserPrs:
    def test_returns_prs_for_user(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"user": {"login": "dependabot[bot]"}, "number": 1, "title": "Bump x"},
            {"user": {"login": "other"}, "number": 2, "title": "Feature"},
        ]
        with patch("requests.get", return_value=mock_response):
            result = auto_merge_prs.get_user_prs("user/repo", "dependabot[bot]")
        assert len(result) == 1
        assert result[0]["number"] == 1

    def test_returns_empty_on_failed_request(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("requests.get", return_value=mock_response):
            result = auto_merge_prs.get_user_prs("user/repo", "dependabot[bot]")
        assert result == []


class TestMergePr:
    def _make_pr(self, number=1, title="Bump x", url="https://github.com/user/repo/pull/1"):
        return {"number": number, "title": title, "html_url": url}

    def test_skips_unmergeable_pr(self):
        details = MagicMock()
        details.json.return_value = {"mergeable": False, "mergeable_state": "dirty"}
        with patch("requests.get", return_value=details):
            auto_merge_prs.merge_pr("user/repo", self._make_pr(), "dependabot[bot]")
        assert len(auto_merge_prs.unmerged_prs) == 1
        assert "Merge conflict" in auto_merge_prs.unmerged_prs[0][4]

    def test_merges_mergeable_pr(self):
        details_response = MagicMock()
        details_response.json.return_value = {"mergeable": True}
        merge_response = MagicMock()
        merge_response.status_code = 200

        with (
            patch("requests.get", return_value=details_response),
            patch("requests.put", return_value=merge_response),
        ):
            auto_merge_prs.merge_pr("user/repo", self._make_pr(), "dependabot[bot]")
        assert len(auto_merge_prs.merged_prs) == 1

    def test_handles_merge_failure(self):
        details_response = MagicMock()
        details_response.json.return_value = {"mergeable": True}
        merge_response = MagicMock()
        merge_response.status_code = 405
        merge_response.json.return_value = {"message": "Not allowed"}

        with (
            patch("requests.get", return_value=details_response),
            patch("requests.put", return_value=merge_response),
        ):
            auto_merge_prs.merge_pr("user/repo", self._make_pr(), "dependabot[bot]")
        assert len(auto_merge_prs.unmerged_prs) == 1
