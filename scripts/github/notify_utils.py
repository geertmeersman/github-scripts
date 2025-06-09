import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === Email Config ===
SMTP_SERVER = os.getenv("SMTP_SERVER")
try:
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
except ValueError:
    print("⚠️ Invalid SMTP_PORT, using default 587")
    SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PWD = os.getenv("SMTP_PWD")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_TO = os.getenv("EMAIL_TO")  # Optional default recipient

# === Telegram Config ===
TELEGRAM_BOT_ID = os.getenv("TELEGRAM_BOT_ID")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_WEBHOOK = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_ID}/sendMessage" if TELEGRAM_BOT_ID else None
)


def send_email_report(subject: str, html_body: str, email_to: str = None):
    """
    Send an HTML email report.

    Args:
        subject (str): Email subject.
        html_body (str): HTML body content.
        email_to (str, optional): Optional override for recipient.
    """
    recipient = email_to or EMAIL_TO
    if not all([SMTP_SERVER, SMTP_USER, SMTP_PWD, EMAIL_FROM, recipient]):
        print("⚠️ Skipping email: SMTP config or recipient missing.")
        return

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PWD)
            server.sendmail(EMAIL_FROM, recipient, msg.as_string())
        print(f"📧 Email sent to {recipient}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def send_telegram_report(text: str):
    """
    Send a raw text message to Telegram using Markdown formatting.

    Args:
        text (str): Message body (Markdown allowed).
    """
    if not TELEGRAM_WEBHOOK or not TELEGRAM_CHAT_ID:
        print("⚠️ Skipping Telegram: config missing.")
        return

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(TELEGRAM_WEBHOOK, json=payload, timeout=10)
        if response.status_code == 200:
            print("📨 Telegram notification sent.")
        else:
            raise Exception(response.text)
    except Exception as e:
        print(f"❌ Telegram notification failed: {e}")
