"""階段 7 測試：HTML 渲染含關鍵區塊與免責、圖檔產生、SMTP 用 mock 寄送。"""
from src.common.disclaimer import DISCLAIMER
from src.report.email_sender import build_email_message, get_recipients, send_email
from src.report.email_view import render_html, render_nav_chart_png
from src.report.model import build_report_model


def _report():
    return build_report_model(
        account_id="main", as_of="2026-05-23", env="paper",
        strategy="nasdaq_momentum_top10", cash=1000.0, equity=10000.0,
        holdings=[{"symbol": "AAPL", "qty": 10,
                   "returns": {"1d": 0.01, "1w": 0.03, "1m": 0.08},
                   "pe_ratio": 30.5}],
        top10=[{"rank": 1, "symbol": "NVDA", "score": 0.25}],
        next_day_candidates=[{"symbol": "NVDA", "score": 0.25}],
        watch_categories=[{"name": "半導體",
                           "symbols": [{"symbol": "NVDA", "pe_ratio": 60.0}]}],
        nav_dates=["2026-05-21", "2026-05-22", "2026-05-23"],
        portfolio_equity_series=[9500, 9800, 10000],
        nasdaq_series=[18000, 18100, 18200],
        sp500_series=[5200, 5210, 5230],
    )


def test_render_html_contains_sections_and_disclaimer():
    html = render_html(_report())
    assert "每日投資日報" in html
    assert "AAPL" in html          # 持倉
    assert "NVDA" in html          # top10 / 類別
    assert "半導體" in html         # 關注類別
    assert "隔日研究參考清單" in html
    assert "cid:navchart" in html  # 圖以 cid 內嵌
    assert DISCLAIMER in html      # 免責頁尾
    assert "不構成投資建議" in html


def test_render_chart_png_is_valid():
    png = render_nav_chart_png(_report())
    assert isinstance(png, bytes) and len(png) > 1000
    assert png[:8] == b"\x89PNG\r\n\x1a\n"  # PNG 檔頭


def test_build_email_message_embeds_image():
    msg = build_email_message(
        sender="me@gmail.com", recipients=["you@x.com"],
        subject="日報", html_body="<html></html>", chart_png=b"\x89PNG\r\n\x1a\nXX",
    )
    assert msg["To"] == "you@x.com"
    assert msg["Subject"] == "日報"
    payloads = msg.get_payload()
    # 應含 alternative(文字) + image
    assert any(p.get_content_maintype() == "image" for p in payloads)


def test_send_email_uses_injected_client(monkeypatch):
    sent = {}

    class FakeSMTP:
        def send_message(self, m):
            sent["msg"] = m

    msg = build_email_message(
        sender="me@gmail.com", recipients=["you@x.com"],
        subject="t", html_body="<html></html>",
    )
    send_email(msg, user="me@gmail.com", password="pw", smtp_client=FakeSMTP())
    assert sent["msg"] is msg


def test_get_recipients(monkeypatch):
    monkeypatch.setenv("REPORT_EMAIL_TO", "a@x.com, b@y.com")
    assert get_recipients() == ["a@x.com", "b@y.com"]
