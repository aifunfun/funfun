"""策略積木庫（building blocks）。

策略 JSON 透過「型別字串」挑選這裡的積木組合。新增同類策略只要寫 JSON；
只有要加「全新一種積木」（例如新的訊號指標）時，才需要在這裡擴充並註冊。
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

# ---- 訊號（signal）積木 ----


def momentum(closes: pd.Series, lookback_days: int = 20) -> float | None:
    """動能：最新收盤相對 lookback_days 個交易日前的報酬率。

    白話：看這檔股票最近一段時間「漲多少」，用來衡量氣勢強弱。資料不足回 None。
    """
    closes = closes.dropna()
    if len(closes) <= lookback_days:
        return None
    last = float(closes.iloc[-1])
    ref = float(closes.iloc[-1 - lookback_days])
    return (last / ref - 1.0) if ref else None


# 訊號註冊表：type 字串 -> 計算函式(closes, **params)
SIGNALS: dict[str, Callable[..., float | None]] = {
    "momentum": momentum,
}


# ---- 配重（sizing）積木 ----


def equal_weight(symbols: list[str], weight_per_position: float) -> dict[str, float]:
    """等權：每檔給固定權重（例如各 10%）。"""
    return {s: weight_per_position for s in symbols}


SIZING: dict[str, Callable[..., dict[str, float]]] = {
    "equal_weight": lambda symbols, cfg: equal_weight(
        symbols, cfg.get("weight_per_position", 1.0 / max(len(symbols), 1))
    ),
}
