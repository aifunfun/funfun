"""階段 2 測試：報酬率計算、基本面優雅降級、選股池排名。"""
from types import SimpleNamespace

import pandas as pd
import pytest

from src.data import fundamentals as fund_mod
from src.data.fundamentals import Fundamentals, get_fundamentals
from src.data.market_data import compute_period_returns, get_daily_closes
from src.data.universe import build_nasdaq_universe


# ---- 報酬率（純函式，用已知序列驗算）----
def test_compute_period_returns_known_series():
    # 連續 30 個收盤價，等差，方便驗算
    closes = pd.Series([100 + i for i in range(30)])  # 100..129
    r = compute_period_returns(closes)
    last = 129
    assert r["1d"] == pytest.approx(last / 128 - 1)
    assert r["1w"] == pytest.approx(last / (closes.iloc[-6]) - 1)
    assert r["1m"] == pytest.approx(last / (closes.iloc[-22]) - 1)


def test_compute_period_returns_insufficient_data():
    closes = pd.Series([100.0, 101.0, 102.0])  # 只有 3 筆
    r = compute_period_returns(closes)
    assert r["1d"] == pytest.approx(102 / 101 - 1)
    assert r["1w"] is None  # 不足 5 日
    assert r["1m"] is None


def test_compute_period_returns_empty():
    r = compute_period_returns(pd.Series(dtype=float))
    assert all(v is None for v in r.values())


# ---- get_daily_closes 優雅降級 ----
def test_get_daily_closes_handles_fetch_error(monkeypatch):
    import sys

    monkeypatch.setitem(
        sys.modules, "alpaca.data.requests",
        SimpleNamespace(StockBarsRequest=lambda **kw: SimpleNamespace(**kw)),
    )
    monkeypatch.setitem(
        sys.modules, "alpaca.data.timeframe",
        SimpleNamespace(TimeFrame=SimpleNamespace(Day="1Day")),
    )

    class BoomClient:
        def get_stock_bars(self, req):
            raise RuntimeError("network down")

    closes = get_daily_closes(BoomClient(), "AAPL")
    assert closes.empty  # 失敗時回空序列，不丟例外


def test_get_daily_closes_parses_dataframe(monkeypatch):
    import sys

    monkeypatch.setitem(
        sys.modules, "alpaca.data.requests",
        SimpleNamespace(StockBarsRequest=lambda **kw: SimpleNamespace(**kw)),
    )
    monkeypatch.setitem(
        sys.modules, "alpaca.data.timeframe",
        SimpleNamespace(TimeFrame=SimpleNamespace(Day="1Day")),
    )
    df = pd.DataFrame({"close": [10.0, 11.0, 12.0]})

    class FakeClient:
        def get_stock_bars(self, req):
            return SimpleNamespace(df=df)

    closes = get_daily_closes(FakeClient(), "AAPL")
    assert list(closes) == [10.0, 11.0, 12.0]


# ---- 基本面優雅降級 ----
def test_get_fundamentals_graceful_on_error(monkeypatch):
    def boom(symbol):
        raise RuntimeError("yfinance down")

    monkeypatch.setattr(fund_mod, "_fetch_info", boom)
    f = get_fundamentals("AAPL")
    assert isinstance(f, Fundamentals)
    assert f.market_cap is None and f.pe_ratio is None


def test_get_fundamentals_parses_info(monkeypatch):
    monkeypatch.setattr(
        fund_mod, "_fetch_info",
        lambda s: {"marketCap": 3_000_000_000_000, "trailingPE": 30.5},
    )
    f = get_fundamentals("AAPL")
    assert f.market_cap == 3_000_000_000_000
    assert f.pe_ratio == 30.5


def test_get_fundamentals_falls_back_to_forward_pe(monkeypatch):
    monkeypatch.setattr(
        fund_mod, "_fetch_info",
        lambda s: {"marketCap": 1.0, "forwardPE": 18.2},
    )
    assert get_fundamentals("X").pe_ratio == 18.2


# ---- 選股池排名 ----
def test_build_universe_ranks_by_market_cap():
    def fake_fetch(syms):
        caps = {"A": 10.0, "B": 30.0, "C": 20.0}
        return {s: Fundamentals(symbol=s, market_cap=caps[s]) for s in syms}

    ranked = build_nasdaq_universe(
        top_n=2, candidates=["A", "B", "C"], fundamentals_fn=fake_fetch
    )
    assert ranked == ["B", "C"]  # 市值最大的兩檔


def test_build_universe_missing_caps_sorted_last():
    def fake_fetch(syms):
        caps = {"A": None, "B": 5.0, "C": None}
        return {s: Fundamentals(symbol=s, market_cap=caps[s]) for s in syms}

    ranked = build_nasdaq_universe(
        top_n=3, candidates=["A", "B", "C"], fundamentals_fn=fake_fetch
    )
    assert ranked[0] == "B"  # 有市值的排最前
    assert set(ranked[1:]) == {"A", "C"}
