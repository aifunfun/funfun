"""每日報告產生 + Email 寄送：走過所有帳戶。

由 GitHub Actions（report.yml）在台灣時間 6:00（UTC 22:00）發動。
    python scripts/run_report.py            # 產報告並存檔；有設 Gmail 環境變數才寄信
    python scripts/run_report.py --no-email # 只產報告不寄信
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.brokers.alpaca_client import AlpacaClient  # noqa: E402
from src.config.accounts import load_accounts  # noqa: E402
from src.config.watchlist import load_watchlist  # noqa: E402
from src.data.adapter import AlpacaDataAdapter  # noqa: E402
from src.orchestrator import build_account_report, equity_history_from_reports  # noqa: E402,E501
from src.report.email_sender import (  # noqa: E402
    build_email_message,
    get_recipients,
    send_email,
)
from src.report.email_view import render_html, render_nav_chart_png  # noqa: E402
from src.report.model import validate_report  # noqa: E402
from src.report.store import list_report_dates, load_report, save_report  # noqa: E402
from src.strategy.engine import StrategyEngine, load_strategy  # noqa: E402


def _maybe_send_email(report: dict) -> bool:
    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    recipients = get_recipients()
    if not (user and pw and recipients):
        print("  未設定 Gmail 環境變數或收件人，略過寄信。")
        return False
    png = render_nav_chart_png(report)
    html = render_html(report)
    msg = build_email_message(
        sender=user, recipients=recipients,
        subject=f"每日投資日報 {report['as_of']} - {report['account_id']}",
        html_body=html, chart_png=png,
    )
    send_email(msg, user=user, password=pw)
    print(f"  已寄信給 {', '.join(recipients)}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--account", default=None)
    args = ap.parse_args()

    cfg = load_accounts()
    accounts = [cfg.get(args.account)] if args.account else cfg.accounts
    as_of = date.today().isoformat()
    watch = load_watchlist()
    failures = 0

    for acc in accounts:
        print(f"\n===== 報告 帳戶 {acc.id} ({acc.env}) =====")
        try:
            client = AlpacaClient.from_account(acc)
            adapter = AlpacaDataAdapter(client)
            strategy = load_strategy(acc.strategy)
            portfolio = StrategyEngine(strategy, adapter).run()

            history = [
                load_report(acc.id, d) for d in list_report_dates(acc.id)
                if d != as_of
            ]
            equity_history = equity_history_from_reports(history)

            report = build_account_report(
                account_id=acc.id, env=acc.env, strategy_name=acc.strategy,
                as_of=as_of, client=client, adapter=adapter,
                portfolio=portfolio, watch_categories=watch,
                equity_history=equity_history,
            )
            validate_report(report)
            path = save_report(report)
            print(f"  報告已存: {path}")
            if not args.no_email:
                _maybe_send_email(report)
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"  帳戶 {acc.id} 報告失敗: {e}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
