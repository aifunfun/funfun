"""每日交易執行：走過所有帳戶，依各自策略買進/賣出。

由 GitHub Actions（trade.yml）發動，也可本機手動跑。
    python scripts/run_trading.py --dry-run        # 只規劃不送單
    python scripts/run_trading.py                  # 實際送單（Paper 帳戶）
    python scripts/run_trading.py --account main   # 只跑指定帳戶
"""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.brokers.alpaca_client import AlpacaClient  # noqa: E402
from src.config.accounts import load_accounts  # noqa: E402
from src.data.adapter import AlpacaDataAdapter  # noqa: E402
from src.execution.notifier import ConsoleNotifier  # noqa: E402
from src.orchestrator import run_trading_for_account  # noqa: E402
from src.portfolio.state_store import load_state, save_state  # noqa: E402
from src.strategy.engine import load_strategy  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--account", default=None, help="只跑此帳戶（預設全部）")
    args = ap.parse_args()

    cfg = load_accounts()
    accounts = (
        [cfg.get(args.account)] if args.account else cfg.accounts
    )
    today = date.today()
    notifier = ConsoleNotifier()
    failures = 0

    for acc in accounts:
        print(f"\n===== 帳戶 {acc.id} ({acc.env}) 策略 {acc.strategy} =====")
        try:
            client = AlpacaClient.from_account(acc)
            adapter = AlpacaDataAdapter(client)
            strategy = load_strategy(acc.strategy)
            state = load_state(acc.id)
            result = run_trading_for_account(
                account_id=acc.id, client=client, adapter=adapter,
                strategy=strategy, today=today, state=state,
                dry_run=args.dry_run, notifier=notifier,
            )
            print(f"再平衡: {result['triggered']}（{result['reason']}）"
                  f" 訂單數: {len(result['orders'])}")
            for r in result["execution"].results:
                print(f"  {r.side} {r.symbol} {r.qty} -> {r.status} {r.detail}")
            if not args.dry_run and result["triggered"]:
                save_state(acc.id, result["state"])
        except Exception as e:  # noqa: BLE001 — 單帳戶失敗不影響其他帳戶
            failures += 1
            print(f"  帳戶 {acc.id} 失敗: {e}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
