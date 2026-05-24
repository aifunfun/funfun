"""選股池：NASDAQ 依市值取前 N 檔。

實務限制：要拿到「完整 NASDAQ 清單」需要外部資料源。這裡內建一份大型
NASDAQ 成分股種子清單（NASDAQ-100 大型股為主），再用 yfinance 的市值排名取前 N。
種子清單可隨時擴充；排名邏輯是純函式，方便測試。
"""
from __future__ import annotations

from typing import Callable

from src.data.fundamentals import Fundamentals, get_fundamentals_batch

# NASDAQ 大型權值股種子清單（可擴充）。僅作為候選池，非投資建議。
NASDAQ_SEED = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "AVGO", "TSLA",
    "COST", "NFLX", "AMD", "PEP", "ADBE", "CSCO", "TMUS", "INTC", "QCOM",
    "INTU", "TXN", "AMGN", "HON", "AMAT", "BKNG", "ISRG", "VRTX", "ADP",
    "REGN", "MU", "LRCX", "PANW", "PYPL", "SBUX", "GILD", "MDLZ", "ADI",
    "KLAC", "SNPS", "CDNS", "MRVL", "ORLY", "CSX", "ASML", "ABNB", "FTNT",
    "CRWD", "CHTR", "NXPI", "PCAR", "MNST",
]


def build_nasdaq_universe(
    top_n: int = 100,
    candidates: list[str] | None = None,
    fundamentals_fn: Callable[[list[str]], dict[str, Fundamentals]] | None = None,
) -> list[str]:
    """回傳依市值由大到小排序的前 top_n 檔股票代號。

    無市值資料（None）的股票會排到最後，確保結果穩定。
    """
    syms = candidates if candidates is not None else NASDAQ_SEED
    fetch = fundamentals_fn or get_fundamentals_batch
    funds = fetch(syms)

    def sort_key(sym: str):
        cap = funds.get(sym).market_cap if funds.get(sym) else None
        # 有市值的排前面（大→小）；無市值的市值視為 -1 排最後
        return (cap is not None, cap if cap is not None else -1.0)

    ranked = sorted(syms, key=sort_key, reverse=True)
    return ranked[:top_n]
