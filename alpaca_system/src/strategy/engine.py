"""JSON 策略引擎：把策略 JSON 直譯成「目標投組（權重）」。

流程：universe（選股池）→ signals（算訊號）→ selection（排名取前 N）→ sizing（配重）。
引擎透過 DataAdapter 取得資料，方便用假資料做單元測試。
整數股的換算在階段 4 的 sizing.py（需要價格與資金），此處只決定權重。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import pandas as pd
from jsonschema import validate as _js_validate

from src.strategy.rules import SIGNALS, SIZING

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "strategies" / "schema.json"
_STRATEGY_DIR = Path(__file__).resolve().parents[2] / "strategies"


class StrategyValidationError(ValueError):
    """策略 JSON 不符合 schema 時拋出。"""


class DataAdapter(Protocol):
    """引擎所需的資料來源介面（正式版接 Alpaca + yfinance；測試版用假資料）。"""

    def build_universe(self, source: str, rank_by: str, top_n: int) -> list[str]: ...

    def get_closes(self, symbol: str) -> pd.Series: ...


@dataclass
class TargetPosition:
    symbol: str
    weight: float
    score: float | None = None  # 入選時的訊號分數（如動能）


@dataclass
class TargetPortfolio:
    strategy_name: str
    positions: list[TargetPosition]
    rebalance: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)

    @property
    def symbols(self) -> list[str]:
        return [p.symbol for p in self.positions]

    def weights(self) -> dict[str, float]:
        return {p.symbol: p.weight for p in self.positions}


def _load_schema() -> dict:
    with _SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_strategy(strategy: dict) -> None:
    try:
        _js_validate(instance=strategy, schema=_load_schema())
    except Exception as e:  # jsonschema.ValidationError 及其他
        raise StrategyValidationError(str(e)) from e


def load_strategy(name_or_path: str | Path) -> dict:
    """以策略名稱（strategies/<name>.json）或完整路徑載入並驗證策略。"""
    path = Path(name_or_path)
    if not path.suffix:
        path = _STRATEGY_DIR / f"{name_or_path}.json"
    if not path.exists():
        raise FileNotFoundError(f"找不到策略檔: {path}")
    with path.open("r", encoding="utf-8") as f:
        strategy = json.load(f)
    validate_strategy(strategy)
    return strategy


class StrategyEngine:
    def __init__(self, strategy: dict, adapter: DataAdapter):
        validate_strategy(strategy)
        self.strategy = strategy
        self.adapter = adapter

    def run(self) -> TargetPortfolio:
        # 1) 選股池
        u = self.strategy["universe"]
        candidates = self.adapter.build_universe(
            u["source"], u.get("rank_by", "market_cap"), u["top_n"]
        )

        # 2) 訊號（目前僅取最後一個訊號作為排名依據；多訊號可日後擴充）
        signals = self.strategy.get("signals", [])
        scores: dict[str, float] = {}
        if signals:
            sig = signals[-1]
            fn = SIGNALS.get(sig["type"])
            if fn is None:
                raise StrategyValidationError(f"未知訊號型別: {sig['type']}")
            params = {k: v for k, v in sig.items() if k != "type"}
            for sym in candidates:
                closes = self.adapter.get_closes(sym)
                val = fn(closes, **params)
                if val is not None:
                    scores[sym] = val
        else:
            scores = {s: 0.0 for s in candidates}

        # 3) 選股：依排名取前 N
        sel = self.strategy["selection"]
        rank_by = sel["rank_by"]
        reverse = sel.get("order", "desc") == "desc"
        if rank_by == "momentum":
            ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=reverse)
            chosen = [(s, sc) for s, sc in ranked[: sel["top_n"]]]
        else:  # market_cap 等：候選池已依序，直接取前 N
            chosen = [(s, scores.get(s, 0.0)) for s in candidates[: sel["top_n"]]]

        chosen_symbols = [s for s, _ in chosen]

        # 4) 配重
        sz = self.strategy["sizing"]
        sizer = SIZING.get(sz["method"])
        if sizer is None:
            raise StrategyValidationError(f"未知配重方法: {sz['method']}")
        weights = sizer(chosen_symbols, sz)

        positions = [
            TargetPosition(symbol=s, weight=weights[s], score=sc)
            for s, sc in chosen
        ]
        return TargetPortfolio(
            strategy_name=self.strategy["name"],
            positions=positions,
            rebalance=self.strategy.get("rebalance", {}),
            constraints=self.strategy.get("constraints", {}),
        )
