"""階段 4 測試：整數股配置、再平衡觸發、買賣單 diff。"""
from datetime import date

from src.portfolio.rebalance import (
    OrderIntent,
    RebalanceState,
    detect_new_cash,
    diff_orders,
    is_new_month,
    should_rebalance,
)
from src.portfolio.sizing import target_allocation_summary, weights_to_target_shares


# ---- 整數股配置 ----
def test_weights_to_integer_shares_floor():
    weights = {"A": 0.10, "B": 0.10}
    prices = {"A": 30.0, "B": 7.0}
    # capital=1000 -> A: 100/30=3.33->3 ; B: 100/7=14.28->14
    shares = weights_to_target_shares(weights, prices, 1000.0)
    assert shares == {"A": 3, "B": 14}
    assert all(isinstance(v, int) for v in shares.values())


def test_sizing_skips_invalid_price():
    shares = weights_to_target_shares({"A": 0.1}, {"A": 0.0}, 1000.0)
    assert shares["A"] == 0


def test_ten_names_each_10pct():
    weights = {c: 0.10 for c in "ABCDEFGHIJ"}
    prices = {c: 100.0 for c in "ABCDEFGHIJ"}
    shares = weights_to_target_shares(weights, prices, 100_000.0)
    # 每檔 10% of 100k = 10k / 100 = 100 股
    assert all(v == 100 for v in shares.values())
    summary = target_allocation_summary(shares, prices, 100_000.0)
    assert all(abs(p - 0.10) < 1e-9 for p in summary.values())


# ---- 再平衡觸發 ----
def test_is_new_month():
    assert is_new_month(date(2026, 2, 1), None) is True
    assert is_new_month(date(2026, 2, 1), date(2026, 1, 31)) is True
    assert is_new_month(date(2026, 1, 15), date(2026, 1, 2)) is False


def test_detect_new_cash():
    assert detect_new_cash(1000.0, 500.0) is True
    assert detect_new_cash(500.5, 500.0) is False  # 在門檻內


def test_should_rebalance_monthly():
    cfg = {"schedule": "monthly_first_trading_day", "on_new_cash": True}
    state = RebalanceState(last_rebalance_date=date(2026, 1, 10), baseline_cash=100.0)
    fire, reason = should_rebalance(cfg, date(2026, 2, 3), state, current_cash=100.0)
    assert fire is True and reason == "monthly_first_trading_day"


def test_should_rebalance_new_cash():
    cfg = {"schedule": "monthly_first_trading_day", "on_new_cash": True}
    state = RebalanceState(last_rebalance_date=date(2026, 2, 1), baseline_cash=100.0)
    fire, reason = should_rebalance(cfg, date(2026, 2, 15), state, current_cash=5000.0)
    assert fire is True and reason == "new_cash"


def test_should_not_rebalance():
    cfg = {"schedule": "monthly_first_trading_day", "on_new_cash": True}
    state = RebalanceState(last_rebalance_date=date(2026, 2, 1), baseline_cash=100.0)
    fire, reason = should_rebalance(cfg, date(2026, 2, 15), state, current_cash=100.0)
    assert fire is False and reason == "no_trigger"


# ---- 買賣單 diff ----
def test_diff_orders_buy_sell_and_liquidate():
    current = {"AAPL": 10, "OLD": 5}
    target = {"AAPL": 15, "MSFT": 8}  # AAPL 加碼、買 MSFT、OLD 出清
    orders = diff_orders(current, target)
    # 先賣後買
    assert orders[0] == OrderIntent("OLD", 5, "sell")
    buys = {o.symbol: o for o in orders if o.side == "buy"}
    assert buys["AAPL"].qty == 5
    assert buys["MSFT"].qty == 8
    assert all(isinstance(o.qty, int) for o in orders)


def test_diff_orders_no_change():
    assert diff_orders({"AAPL": 10}, {"AAPL": 10}) == []
