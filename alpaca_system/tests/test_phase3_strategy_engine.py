"""階段 3 測試：策略 JSON 驗證、引擎產出目標投組、換 JSON 不改 Python。"""
import json

import pandas as pd
import pytest

from src.strategy.engine import (
    StrategyEngine,
    StrategyValidationError,
    TargetPortfolio,
    load_strategy,
    validate_strategy,
)


class FakeAdapter:
    """假資料：5 檔候選股，動能由 A>B>C>D>E。"""

    def __init__(self):
        self._mom = {"A": 0.5, "B": 0.4, "C": 0.3, "D": 0.2, "E": 0.1}

    def build_universe(self, source, rank_by, top_n):
        return ["A", "B", "C", "D", "E"][:top_n]

    def get_closes(self, symbol):
        # 造一條序列，使 momentum(lookback=2) = 指定值
        base = 100.0
        target = base * (1 + self._mom[symbol])
        return pd.Series([base, base, target])


def _valid_strategy(top_n_sel=3, weight=0.10):
    return {
        "name": "t",
        "universe": {"source": "nasdaq", "rank_by": "market_cap", "top_n": 5},
        "signals": [{"type": "momentum", "lookback_days": 2}],
        "selection": {"rank_by": "momentum", "order": "desc", "top_n": top_n_sel},
        "sizing": {"method": "equal_weight", "weight_per_position": weight,
                   "shares": "integer"},
        "rebalance": {"schedule": "monthly_first_trading_day", "on_new_cash": True},
        "constraints": {"long_only": True, "max_positions": top_n_sel},
    }


# ---- schema 驗證 ----
def test_valid_strategy_passes():
    validate_strategy(_valid_strategy())  # 不應拋錯


def test_invalid_strategy_rejected():
    bad = _valid_strategy()
    del bad["universe"]
    with pytest.raises(StrategyValidationError):
        validate_strategy(bad)


def test_unknown_field_rejected():
    bad = _valid_strategy()
    bad["wat"] = 1
    with pytest.raises(StrategyValidationError):
        validate_strategy(bad)


def test_bundled_example_strategy_is_valid():
    s = load_strategy("nasdaq_momentum_top10")
    assert s["name"] == "nasdaq_momentum_top10"
    assert s["sizing"]["weight_per_position"] == 0.10


# ---- 引擎產出 ----
def test_engine_selects_top_momentum_and_equal_weight():
    eng = StrategyEngine(_valid_strategy(top_n_sel=3, weight=0.10), FakeAdapter())
    port = eng.run()
    assert isinstance(port, TargetPortfolio)
    assert port.symbols == ["A", "B", "C"]  # 動能前三
    # 每檔權重各 10%
    assert all(abs(w - 0.10) < 1e-9 for w in port.weights().values())
    assert len(port.positions) == 3


def test_engine_respects_top10_and_weight():
    # 模擬「前 10 檔各 10%」的需求
    adapter = FakeAdapter()
    adapter._mom = {c: i / 100 for i, c in enumerate("ABCDEFGHIJKL")}
    adapter.build_universe = lambda s, r, n: list("ABCDEFGHIJKL")[:n]
    strat = _valid_strategy(top_n_sel=10, weight=0.10)
    strat["universe"]["top_n"] = 12
    port = StrategyEngine(strat, adapter).run()
    assert len(port.positions) == 10
    assert sum(port.weights().values()) == pytest.approx(1.0)  # 10 檔 * 10%


def test_new_strategy_via_json_only_no_python_change(tmp_path):
    # 只改 JSON 參數（選 2 檔、各 20%），不動任何 Python，引擎照樣跑
    strat = _valid_strategy(top_n_sel=2, weight=0.20)
    p = tmp_path / "custom.json"
    p.write_text(json.dumps(strat), encoding="utf-8")
    loaded = load_strategy(p)
    port = StrategyEngine(loaded, FakeAdapter()).run()
    assert port.symbols == ["A", "B"]
    assert all(abs(w - 0.20) < 1e-9 for w in port.weights().values())
