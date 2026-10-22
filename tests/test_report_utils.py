import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "github"))

from report_utils import wrap_html_report


class TestWrapHtmlReport:
    def test_returns_html_string(self):
        result = wrap_html_report("<p>content</p>")
        assert "<!DOCTYPE html>" in result
        assert "<p>content</p>" in result

    def test_includes_title(self):
        result = wrap_html_report("<p>x</p>", title="My Report")
        assert "My Report" in result

    def test_includes_github_user(self):
        result = wrap_html_report("<p>x</p>", github_user="testuser")
        assert "testuser" in result

    def test_escapes_xss_in_title(self):
        result = wrap_html_report("<p>x</p>", title="<script>alert(1)</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_escapes_xss_in_github_user(self):
        result = wrap_html_report("<p>x</p>", github_user="<script>alert(1)</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_writes_to_file(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        wrap_html_report("<p>content</p>", output_path=path)
        content = Path(path).read_text()
        assert "<p>content</p>" in content

    def test_raises_on_unwritable_path(self):
        with pytest.raises(OSError):
            wrap_html_report("<p>x</p>", output_path="/proc/sys/kernel/hostname/report.html")
