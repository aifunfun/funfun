"""行情資料：歷史日線與報酬率計算。

- 從 Alpaca 取日線收盤序列（供 NAV、動能、報酬率使用）。
- compute_period_returns 是純函式，吃一條收盤價序列，算 1日/1週/1月報酬，方便測試。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

# 各期間約略的「交易日」數
TRADING_DAYS = {"1d": 1, "1w": 5, "1m": 21}


def compute_period_returns(closes: pd.Series) -> dict[str, float | None]:
    """用收盤價序列算各期間報酬率（小數，0.05 = +5%）。

    closes 需依時間由舊到新排序。資料不足的期間回傳 None。
    """
    closes = closes.dropna()
    out: dict[str, float | None] = {}
    if len(closes) < 2:
        return {k: None for k in TRADING_DAYS}
    last = float(closes.iloc[-1])
    for label, n in TRADING_DAYS.items():
        if len(closes) > n:
            ref = float(closes.iloc[-1 - n])
            out[label] = (last / ref - 1.0) if ref else None
        else:
            out[label] = None
    return out


def get_daily_closes(
    data_client: Any, symbol: str, lookback_days: int = 40
) -> pd.Series:
    """從 Alpaca 取近 lookback_days 個日曆日的日線收盤，回傳 pandas Series。

    抓不到資料時回傳空 Series（優雅降級，不丟例外）。
    """
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
    )
    try:
        bars = data_client.get_stock_bars(req)
    except Exception:  # noqa: BLE001 — 行情失敗時降級為空序列
        return pd.Series(dtype=float)

    df = getattr(bars, "df", None)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    # 多檔時為 MultiIndex (symbol, timestamp)
    if isinstance(df.index, pd.MultiIndex):
        if symbol not in df.index.get_level_values(0):
            return pd.Series(dtype=float)
        df = df.xs(symbol, level=0)
    return df["close"].astype(float)


def get_returns_for_symbols(
    data_client: Any, symbols: list[str], lookback_days: int = 40
) -> dict[str, dict[str, float | None]]:
    """批次取得多檔股票的 1日/1週/1月報酬。"""
    result: dict[str, dict[str, float | None]] = {}
    for sym in symbols:
        closes = get_daily_closes(data_client, sym, lookback_days)
        result[sym] = compute_period_returns(closes)
    return result
