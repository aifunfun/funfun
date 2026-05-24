"""階段 5 測試：送單、dry-run、單筆失敗不中斷、即時通知含免責。"""
from types import SimpleNamespace

from src.common.disclaimer import DISCLAIMER
from src.execution.notifier import (
    ConsoleNotifier,
    format_batch_message,
    format_trade_message,
)
from src.execution.trader import ExecutionResult, execute_orders
from src.portfolio.rebalance import OrderIntent


class FakeClient:
    def __init__(self, fail_symbols=None):
        self.fail_symbols = set(fail_symbols or [])
        self.calls = []

    def submit_market_order(self, symbol, qty, side):
        self.calls.append((symbol, qty, side))
        if symbol in self.fail_symbols:
            raise RuntimeError("market is closed")
        return SimpleNamespace(id=f"ord-{symbol}", status="accepted")


def test_dry_run_does_not_submit():
    client = FakeClient()
    orders = [OrderIntent("AAPL", 5, "buy"), OrderIntent("MSFT", 3, "sell")]
    report = execute_orders(client, "main", orders, dry_run=True)
    assert client.calls == []  # 沒有真的送單
    assert all(r.status == "planned" for r in report.results)
    assert report.dry_run is True


def test_submit_success():
    client = FakeClient()
    orders = [OrderIntent("AAPL", 5, "buy")]
    report = execute_orders(client, "main", orders)
    assert client.calls == [("AAPL", 5, "buy")]
    assert len(report.submitted) == 1
    assert report.submitted[0].detail == "ord-AAPL"


def test_single_failure_does_not_stop_batch():
    client = FakeClient(fail_symbols=["BAD"])
    orders = [
        OrderIntent("BAD", 5, "buy"),
        OrderIntent("AAPL", 2, "buy"),
    ]
    report = execute_orders(client, "main", orders)
    assert len(report.failed) == 1
    assert report.failed[0].symbol == "BAD"
    assert "market is closed" in report.failed[0].detail
    assert len(report.submitted) == 1  # AAPL 仍送出


def test_notifier_receives_messages_with_disclaimer():
    client = FakeClient()
    notifier = ConsoleNotifier()
    execute_orders(client, "main", [OrderIntent("AAPL", 1, "buy")], notifier=notifier)
    assert len(notifier.sent) == 1
    subject, body = notifier.sent[0]
    assert "AAPL" in subject
    assert DISCLAIMER in body


def test_format_trade_message_contains_disclaimer():
    res = ExecutionResult("AAPL", 5, "buy", "submitted", "ord-1")
    msg = format_trade_message("main", res)
    assert "買進" in msg and "AAPL" in msg
    assert DISCLAIMER in msg


def test_format_batch_message_empty_and_nonempty():
    assert DISCLAIMER in format_batch_message("main", [])
    res = [ExecutionResult("AAPL", 5, "buy", "submitted")]
    msg = format_batch_message("main", res)
    assert "共 1 筆" in msg and DISCLAIMER in msg
