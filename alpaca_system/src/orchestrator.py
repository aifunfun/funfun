"""把各模組串成「每帳戶」的交易與報告流程。

交易流程：策略引擎 → 目標權重 → 整數股 → 再平衡判斷 → 買賣單 diff → 執行。
報告流程：彙整現金/持倉/報酬/本益比/Top10/隔日清單/關注類別/NAV與大盤對比 → JSON。

為了可測試，函式接受已建好的 client / adapter / strategy；
正式執行由 scripts/run_trading.py、scripts/run_report.py 注入真實依賴。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable

from src.data.benchmarks import NASDAQ_PROXY, SP500_PROXY, get_closes_for_dates
from src.data.fundamentals import get_fundamentals
from src.data.market_data import compute_period_returns
from src.execution.notifier import Notifier, format_batch_message
from src.execution.trader import ExecutionReport, execute_orders
from src.portfolio.rebalance import (
    OrderIntent,
    RebalanceState,
    diff_orders,
    should_rebalance,
)
from src.portfolio.sizing import weights_to_target_shares
from src.report.model import build_report_model
from src.strategy.engine import StrategyEngine, TargetPortfolio


# ---------------- 交易 ----------------
def run_trading_for_account(
    *,
    account_id: str,
    client,
    adapter,
    strategy: dict,
    today: date,
    state: RebalanceState,
    dry_run: bool = False,
    notifier: Notifier | None = None,
) -> dict[str, Any]:
    """執行單一帳戶的買賣。回傳含觸發原因、訂單、執行結果與更新後狀態。"""
    port: TargetPortfolio = StrategyEngine(strategy, adapter).run()
    acc = client.get_account()

    fire, reason = should_rebalance(port.rebalance, today, state, acc.cash)
    if not fire:
        return {
            "triggered": False,
            "reason": reason,
            "orders": [],
            "execution": ExecutionReport(account_id=account_id, dry_run=dry_run),
            "state": state,
            "portfolio": port,
        }

    prices = client.get_latest_prices(port.symbols)
    target_shares = weights_to_target_shares(port.weights(), prices, acc.equity)
    current = {p.symbol: int(p.qty) for p in client.get_positions()}
    orders: list[OrderIntent] = diff_orders(current, target_shares)

    report = execute_orders(
        client, account_id, orders, dry_run=dry_run, notifier=notifier
    )

    new_state = state
    if not dry_run:
        new_state = RebalanceState(
            last_rebalance_date=today, baseline_cash=acc.cash
        )

    if notifier is not None:
        notifier.notify(
            subject=f"再平衡彙總 - {account_id}",
            body=format_batch_message(account_id, report.results),
        )

    return {
        "triggered": True,
        "reason": reason,
        "orders": orders,
        "execution": report,
        "state": new_state,
        "portfolio": port,
    }


# ---------------- 報告 ----------------
def build_account_report(
    *,
    account_id: str,
    env: str,
    strategy_name: str,
    as_of: str,
    client,
    adapter,
    portfolio: TargetPortfolio,
    watch_categories: list[dict],
    equity_history: list[tuple[str, float]],
    rebalance_info: dict | None = None,
    fundamentals_fn: Callable[[str], Any] = get_fundamentals,
    benchmark_fn: Callable[[str, list[str]], list[float]] = get_closes_for_dates,
) -> dict[str, Any]:
    """彙整單一帳戶的每日報告 JSON（Model）。"""
    acc = client.get_account()
    positions = client.get_positions()

    # 持倉：報酬率 + 本益比
    holdings = []
    for p in positions:
        closes = adapter.get_closes(p.symbol)
        rets = compute_period_returns(closes)
        f = fundamentals_fn(p.symbol)
        holdings.append(
            {
                "symbol": p.symbol,
                "qty": int(p.qty),
                "market_value": round(p.market_value, 2),
                "avg_entry_price": p.avg_entry_price,
                "unrealized_plpc": p.unrealized_plpc,
                "returns": rets,
                "pe_ratio": getattr(f, "pe_ratio", None),
            }
        )

    # Top10 / 隔日研究參考清單（皆來自策略選出的標的與分數）
    top10 = [
        {"rank": i + 1, "symbol": pos.symbol, "score": pos.score}
        for i, pos in enumerate(portfolio.positions[:10])
    ]
    next_day = [{"symbol": pos.symbol, "score": pos.score}
                for pos in portfolio.positions[:10]]

    # 關注類別：補上本益比
    cats = []
    for cat in watch_categories:
        syms = []
        for sym in cat.get("symbols", []):
            f = fundamentals_fn(sym)
            syms.append({"symbol": sym, "pe_ratio": getattr(f, "pe_ratio", None)})
        cats.append({"name": cat["name"], "symbols": syms})

    # NAV：歷史資產 + 今日；大盤對比抓 QQQ / SPY
    dates = [d for d, _ in equity_history] + [as_of]
    equities = [e for _, e in equity_history] + [acc.equity]
    nasdaq = benchmark_fn(NASDAQ_PROXY, dates)
    sp500 = benchmark_fn(SP500_PROXY, dates)

    return build_report_model(
        account_id=account_id,
        as_of=as_of,
        env=env,
        strategy=strategy_name,
        cash=acc.cash,
        equity=acc.equity,
        holdings=holdings,
        top10=top10,
        next_day_candidates=next_day,
        watch_categories=cats,
        nav_dates=dates,
        portfolio_equity_series=equities,
        nasdaq_series=nasdaq or None,
        sp500_series=sp500 or None,
        rebalance=rebalance_info or {"triggered": False, "reason": "no_trigger"},
    )


def equity_history_from_reports(reports: list[dict]) -> list[tuple[str, float]]:
    """從歷史報告 list 抽出 (日期, 總資產) 序列，依日期排序。"""
    rows = [(r["as_of"], float(r["equity"])) for r in reports if "equity" in r]
    return sorted(rows, key=lambda x: x[0])
