import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "github"))

import notify_utils


@pytest.fixture(autouse=True)
def reset_module_globals():
    """Reset module-level config between tests."""
    original = {
        k: getattr(notify_utils, k)
        for k in [
            "SMTP_SERVER",
            "SMTP_USER",
            "SMTP_PWD",
            "EMAIL_FROM",
            "EMAIL_TO",
            "TELEGRAM_WEBHOOK",
            "TELEGRAM_CHAT_ID",
        ]
    }
    yield
    for k, v in original.items():
        setattr(notify_utils, k, v)


class TestSendEmailReport:
    def test_skips_when_smtp_config_missing(self, capsys):
        notify_utils.SMTP_SERVER = None
        notify_utils.send_email_report("subject", "<p>body</p>")
        assert "Skipping email" in capsys.readouterr().out

    def test_skips_when_recipient_missing(self, capsys):
        notify_utils.SMTP_SERVER = "smtp.example.com"
        notify_utils.SMTP_USER = "user@example.com"
        notify_utils.SMTP_PWD = "password"
        notify_utils.EMAIL_FROM = "user@example.com"
        notify_utils.EMAIL_TO = None
        notify_utils.send_email_report("subject", "<p>body</p>")
        assert "Skipping email" in capsys.readouterr().out

    def test_sends_email_successfully(self, capsys):
        notify_utils.SMTP_SERVER = "smtp.example.com"
        notify_utils.SMTP_USER = "user@example.com"
        notify_utils.SMTP_PWD = "password"
        notify_utils.EMAIL_FROM = "user@example.com"
        notify_utils.EMAIL_TO = "to@example.com"

        mock_smtp = MagicMock()
        with patch("smtplib.SMTP", return_value=mock_smtp.__enter__.return_value):
            notify_utils.send_email_report("subject", "<p>body</p>")

    def test_handles_smtp_exception(self, capsys):
        notify_utils.SMTP_SERVER = "smtp.example.com"
        notify_utils.SMTP_USER = "user@example.com"
        notify_utils.SMTP_PWD = "password"
        notify_utils.EMAIL_FROM = "user@example.com"
        notify_utils.EMAIL_TO = "to@example.com"

        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
            notify_utils.send_email_report("subject", "<p>body</p>")
        assert "Failed to send email" in capsys.readouterr().out

    def test_uses_override_recipient(self, capsys):
        notify_utils.SMTP_SERVER = None
        notify_utils.send_email_report("subject", "<p>body</p>", email_to="override@example.com")
        assert "Skipping email" in capsys.readouterr().out


class TestSendTelegramReport:
    def test_skips_when_config_missing(self, capsys):
        notify_utils.TELEGRAM_WEBHOOK = None
        notify_utils.TELEGRAM_CHAT_ID = None
        notify_utils.send_telegram_report("hello")
        assert "Skipping Telegram" in capsys.readouterr().out

    def test_sends_successfully(self, capsys):
        notify_utils.TELEGRAM_WEBHOOK = "https://api.telegram.org/bot123/sendMessage"
        notify_utils.TELEGRAM_CHAT_ID = "456"

        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("requests.post", return_value=mock_response):
            notify_utils.send_telegram_report("hello")
        assert "Telegram notification sent" in capsys.readouterr().out

    def test_handles_failed_response(self, capsys):
        notify_utils.TELEGRAM_WEBHOOK = "https://api.telegram.org/bot123/sendMessage"
        notify_utils.TELEGRAM_CHAT_ID = "456"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        with patch("requests.post", return_value=mock_response):
            notify_utils.send_telegram_report("hello")
        assert "Telegram notification failed" in capsys.readouterr().out
