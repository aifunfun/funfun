"""報告用的數學：NAV（淨值曲線）、回撤、基準正規化。

全為純函式，吃 list/Series，方便用已知數列驗算。
- NAV：把資產序列正規化到共同基準（預設 100），方便和大盤比較。
- 回撤(drawdown)：白話是「從最高點往下掉了多少%」，負值越大代表跌越深。
"""
from __future__ import annotations


def normalize_to_base(values: list[float], base: float = 100.0) -> list[float]:
    """把序列正規化，使第一個值等於 base（用於 NAV 與大盤對比）。"""
    clean = [v for v in values if v is not None]
    if not clean or clean[0] == 0:
        return [base for _ in values]
    first = clean[0]
    return [base * (v / first) if v is not None else None for v in values]


def compute_nav_series(equity_values: list[float], base: float = 100.0) -> list[float]:
    """資產序列 → NAV 曲線（正規化到 base）。"""
    return normalize_to_base(equity_values, base)


def compute_drawdown(nav_values: list[float]) -> list[float]:
    """回撤序列：每點 = 目前淨值 / 歷史最高 - 1（<=0）。"""
    out: list[float] = []
    peak = float("-inf")
    for v in nav_values:
        if v is None:
            out.append(0.0)
            continue
        peak = max(peak, v)
        out.append((v / peak - 1.0) if peak > 0 else 0.0)
    return out


def max_drawdown(nav_values: list[float]) -> float:
    """最大回撤（最深的那個負值）。"""
    dd = compute_drawdown(nav_values)
    return min(dd) if dd else 0.0
