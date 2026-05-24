"""階段 9 測試：交易流程（觸發/不觸發/dry-run）、報告產生+存檔、workflow 設定。"""
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from src.brokers.alpaca_client import AccountInfo, Position
from src.orchestrator import (
    build_account_report,
    equity_history_from_reports,
    run_trading_for_account,
)
from src.portfolio.rebalance import RebalanceState
from src.report.model import validate_report
from src.report.store import load_report, save_report

REPO_ROOT = Path(__file__).resolve().parents[2]  # G:\funfun


class FakeClient:
    def __init__(self, equity=10000.0, cash=10000.0, positions=None, fail=None):
        self._equity = equity
        self._cash = cash
        self._positions = positions or []
        self._fail = set(fail or [])
        self.submitted = []

    def get_account(self):
        return AccountInfo(cash=self._cash, equity=self._equity, buying_power=self._cash)

    def get_latest_prices(self, symbols):
        return {s: 100.0 for s in symbols}

    def get_positions(self):
        return self._positions

    def submit_market_order(self, symbol, qty, side):
        if symbol in self._fail:
            raise RuntimeError("boom")
        self.submitted.append((symbol, qty, side))
        return SimpleNamespace(id=f"o-{symbol}", status="accepted")


class FakeAdapter:
    def build_universe(self, source, rank_by, top_n):
        return ["A", "B", "C", "D"][:top_n]

    def get_closes(self, symbol):
        return pd.Series([90.0, 95.0, 100.0])


def _strategy(top_n_sel=3, weight=0.10):
    return {
        "name": "t",
        "universe": {"source": "nasdaq", "rank_by": "market_cap", "top_n": 4},
        "signals": [{"type": "momentum", "lookback_days": 1}],
        "selection": {"rank_by": "momentum", "order": "desc", "top_n": top_n_sel},
        "sizing": {"method": "equal_weight", "weight_per_position": weight},
        "rebalance": {"schedule": "monthly_first_trading_day", "on_new_cash": True},
        "constraints": {"long_only": True, "max_positions": top_n_sel},
    }


def test_trading_triggers_and_submits():
    client = FakeClient(equity=10000.0, cash=10000.0)
    state = RebalanceState()  # 從未再平衡 -> 觸發
    res = run_trading_for_account(
        account_id="main", client=client, adapter=FakeAdapter(),
        strategy=_strategy(), today=date(2026, 5, 1), state=state, dry_run=False,
    )
    assert res["triggered"] is True
    # 每檔 10% of 10000 / 100 = 10 股，共 3 檔
    assert sorted(client.submitted) == [("A", 10, "buy"), ("B", 10, "buy"),
                                        ("C", 10, "buy")]
    assert res["state"].last_rebalance_date == date(2026, 5, 1)


def test_trading_no_trigger_no_orders():
    client = FakeClient()
    state = RebalanceState(last_rebalance_date=date(2026, 5, 10), baseline_cash=10000.0)
    res = run_trading_for_account(
        account_id="main", client=client, adapter=FakeAdapter(),
        strategy=_strategy(), today=date(2026, 5, 20), state=state, dry_run=False,
    )
    assert res["triggered"] is False
    assert client.submitted == []


def test_trading_dry_run_does_not_submit():
    client = FakeClient()
    res = run_trading_for_account(
        account_id="main", client=client, adapter=FakeAdapter(),
        strategy=_strategy(), today=date(2026, 5, 1),
        state=RebalanceState(), dry_run=True,
    )
    assert res["triggered"] is True
    assert client.submitted == []  # dry-run 不送單
    assert all(r.status == "planned" for r in res["execution"].results)


def test_build_report_and_save(tmp_path):
    from src.strategy.engine import StrategyEngine

    client = FakeClient(positions=[
        Position("A", 10, 90.0, 1000.0, 100.0, 100.0, 0.11)
    ])
    adapter = FakeAdapter()
    portfolio = StrategyEngine(_strategy(), adapter).run()

    report = build_account_report(
        account_id="main", env="paper", strategy_name="t", as_of="2026-05-23",
        client=client, adapter=adapter, portfolio=portfolio,
        watch_categories=[{"name": "半導體", "symbols": ["A", "B"]}],
        equity_history=[("2026-05-21", 9500.0), ("2026-05-22", 9800.0)],
        fundamentals_fn=lambda s: SimpleNamespace(pe_ratio=25.0),
        benchmark_fn=lambda sym, dates: [100.0 + i for i in range(len(dates))],
    )
    validate_report(report)
    assert report["holdings"][0]["symbol"] == "A"
    assert report["holdings"][0]["pe_ratio"] == 25.0
    assert len(report["top10"]) == 3
    assert report["nav"]["nasdaq"]  # 有大盤對比
    # round-trip
    save_report(report, root=tmp_path)
    assert load_report("main", "2026-05-23", root=tmp_path)["account_id"] == "main"


def test_equity_history_from_reports_sorted():
    reports = [
        {"as_of": "2026-05-22", "equity": 9800},
        {"as_of": "2026-05-21", "equity": 9500},
    ]
    assert equity_history_from_reports(reports) == [
        ("2026-05-21", 9500.0), ("2026-05-22", 9800.0)
    ]


# ---- workflow 設定檢查 ----
def test_trade_workflow_has_cron_and_dry_run():
    text = (REPO_ROOT / ".github" / "workflows" / "trade.yml").read_text(encoding="utf-8")
    assert "cron:" in text and "* * 1-5" in text
    assert "dry_run" in text
    assert "working-directory: alpaca_system" in text
    assert "run_trading.py" in text


def test_report_workflow_has_taiwan_6am_cron():
    text = (REPO_ROOT / ".github" / "workflows" / "report.yml").read_text(encoding="utf-8")
    # 台灣 6:00 = UTC 22:00
    assert "0 22 * * 1-5" in text
    assert "run_report.py" in text
    assert "contents: write" in text
