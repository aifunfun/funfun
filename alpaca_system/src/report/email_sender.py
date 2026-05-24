"""Gmail SMTP 寄信。

用 Gmail 帳號 + 「應用程式密碼」（不是登入密碼）寄出 HTML 日報，並內嵌 NAV 圖。
帳密由環境變數提供：
    GMAIL_USER      寄件 Gmail 地址
    GMAIL_APP_PASSWORD  Google 應用程式密碼
    REPORT_EMAIL_TO 收件地址（可逗號分隔多位）
"""
from __future__ import annotations

import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


def build_email_message(
    *,
    sender: str,
    recipients: list[str],
    subject: str,
    html_body: str,
    chart_png: bytes | None = None,
    chart_cid: str = "navchart",
) -> MIMEMultipart:
    """組出含內嵌圖的 multipart/related 郵件物件（純函式，方便測試）。"""
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    if chart_png:
        img = MIMEImage(chart_png, _subtype="png")
        img.add_header("Content-ID", f"<{chart_cid}>")
        img.add_header("Content-Disposition", "inline", filename="nav.png")
        msg.attach(img)
    return msg


def send_email(
    msg: MIMEMultipart,
    *,
    user: str | None = None,
    password: str | None = None,
    smtp_client=None,
) -> None:
    """實際送出。可注入 smtp_client 以利測試。"""
    user = user or os.environ["GMAIL_USER"]
    password = password or os.environ["GMAIL_APP_PASSWORD"]

    if smtp_client is None:
        with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
    else:
        smtp_client.send_message(msg)


def get_recipients() -> list[str]:
    raw = os.environ.get("REPORT_EMAIL_TO", "")
    return [r.strip() for r in raw.split(",") if r.strip()]
