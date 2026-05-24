"""大盤對比資料：NASDAQ 用 QQQ、S&P 500 用 SPY 作為代理（proxy）。

白話：QQQ、SPY 是追蹤這兩個指數的 ETF，用它們的走勢當大盤比較基準。
資料來自 yfinance（非官方、可能延遲），失敗時優雅降級回空清單。
"""
from __future__ import annotations

NASDAQ_PROXY = "QQQ"
SP500_PROXY = "SPY"


def _fetch_history(symbol: str, start: str, end: str):
    """抓 yfinance 日線（抽出方便測試 monkeypatch）。回傳 DataFrame。"""
    import yfinance as yf

    return yf.Ticker(symbol).history(start=start, end=end)


def get_closes_for_dates(symbol: str, dates: list[str]) -> list[float]:
    """回傳對齊 dates（YYYY-MM-DD 字串）的收盤價清單；缺值以前值填補。

    任一步失敗都回空清單（讓報告仍可產生，只是少了該條對比線）。
    """
    if not dates:
        return []
    try:
        import pandas as pd

        hist = _fetch_history(symbol, dates[0], _next_day(dates[-1]))
        if hist is None or hist.empty:
            return []
        closes = hist["Close"]
        closes.index = [d.strftime("%Y-%m-%d") for d in closes.index]
        s = pd.Series(closes.to_dict())
        aligned = s.reindex(dates).ffill().bfill()
        return [float(v) for v in aligned.tolist()]
    except Exception:  # noqa: BLE001
        return []


def _next_day(date_str: str) -> str:
    from datetime import date, timedelta

    d = date.fromisoformat(date_str) + timedelta(days=1)
    return d.isoformat()
