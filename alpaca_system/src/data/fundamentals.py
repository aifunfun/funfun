"""基本面資料：市值與本益比（P/E），資料來源為 yfinance。

白話提醒：yfinance 是非官方來源，欄位可能延遲或抓不到，**僅供參考**。
任何一檔抓取失敗都不會讓整批崩潰（優雅降級，缺值以 None 表示）。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Fundamentals:
    symbol: str
    market_cap: float | None = None  # 市值
    pe_ratio: float | None = None    # 本益比（股價 / 每股盈餘）


def _fetch_info(symbol: str) -> dict:
    """實際呼叫 yfinance 取得個股資訊。抽出成函式方便測試時 monkeypatch。"""
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    return ticker.info or {}


def get_fundamentals(symbol: str) -> Fundamentals:
    """取得單一股票的市值與本益比；失敗回傳含 None 的物件。"""
    try:
        info = _fetch_info(symbol)
    except Exception:  # noqa: BLE001 — 來源不穩，降級為缺值
        return Fundamentals(symbol=symbol)

    market_cap = info.get("marketCap")
    # yfinance 的本益比常見欄位：trailingPE，其次 forwardPE
    pe = info.get("trailingPE")
    if pe is None:
        pe = info.get("forwardPE")

    return Fundamentals(
        symbol=symbol,
        market_cap=float(market_cap) if isinstance(market_cap, (int, float)) else None,
        pe_ratio=float(pe) if isinstance(pe, (int, float)) else None,
    )


def get_fundamentals_batch(symbols: list[str]) -> dict[str, Fundamentals]:
    return {sym: get_fundamentals(sym) for sym in symbols}
