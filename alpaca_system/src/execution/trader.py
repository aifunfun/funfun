"""執行層：把買賣單送到 Alpaca（Paper），逐筆處理成功/失敗並可即時通知。

設計重點：
- 單筆失敗（休市、買力不足等）不會中斷整批，會記錄錯誤後繼續。
- 支援 dry_run：只規劃不送單，方便在 CI 先驗證。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.execution.notifier import Notifier, format_trade_message
from src.portfolio.rebalance import OrderIntent


@dataclass
class ExecutionResult:
    symbol: str
    qty: int
    side: str
    status: str           # planned / submitted / failed
    detail: str = ""      # 訂單 id 或錯誤訊息


@dataclass
class ExecutionReport:
    account_id: str
    results: list[ExecutionResult] = field(default_factory=list)
    dry_run: bool = False

    @property
    def submitted(self) -> list[ExecutionResult]:
        return [r for r in self.results if r.status == "submitted"]

    @property
    def failed(self) -> list[ExecutionResult]:
        return [r for r in self.results if r.status == "failed"]


def execute_orders(
    client,
    account_id: str,
    orders: list[OrderIntent],
    *,
    dry_run: bool = False,
    notifier: Notifier | None = None,
) -> ExecutionReport:
    """送出一批買賣單。"""
    report = ExecutionReport(account_id=account_id, dry_run=dry_run)

    for order in orders:
        if dry_run:
            res = ExecutionResult(
                order.symbol, order.qty, order.side, "planned", "dry_run"
            )
            report.results.append(res)
            continue

        try:
            o = client.submit_market_order(order.symbol, order.qty, order.side)
            res = ExecutionResult(
                order.symbol, order.qty, order.side, "submitted", detail=o.id
            )
        except Exception as e:  # noqa: BLE001 — 單筆失敗不中斷整批
            res = ExecutionResult(
                order.symbol, order.qty, order.side, "failed", detail=str(e)
            )

        report.results.append(res)
        if notifier is not None:
            notifier.notify(
                subject=f"交易通知 - {account_id} {order.symbol}",
                body=format_trade_message(account_id, res),
            )

    return report
