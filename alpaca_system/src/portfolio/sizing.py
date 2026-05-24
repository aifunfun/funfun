"""配置部位大小：把目標權重 + 價格 + 可投入資金，換算成「整數股」目標。

規則（依需求）：
- 前十檔每檔投入 10%（權重由策略 JSON 決定）。
- 只買整數股：股數一律無條件捨去（floor），不會出現碎股。
- 價格無效（<=0 或缺）者跳過。
"""
from __future__ import annotations

import math


def weights_to_target_shares(
    weights: dict[str, float],
    prices: dict[str, float],
    capital: float,
) -> dict[str, int]:
    """回傳每檔的目標整數股數。

    capital：本次可配置的總資金（通常為帳戶總資產 equity）。
    某檔 = floor(capital * weight / price)。
    """
    target: dict[str, int] = {}
    for symbol, weight in weights.items():
        price = prices.get(symbol, 0.0)
        if price <= 0 or weight <= 0 or capital <= 0:
            target[symbol] = 0
            continue
        dollars = capital * weight
        shares = math.floor(dollars / price)
        target[symbol] = int(max(shares, 0))
    return target


def target_allocation_summary(
    target_shares: dict[str, int], prices: dict[str, float], capital: float
) -> dict[str, float]:
    """回傳每檔實際配置金額占比（用來檢查與 10% 目標的落差，零頭屬正常）。"""
    summary: dict[str, float] = {}
    if capital <= 0:
        return {s: 0.0 for s in target_shares}
    for s, qty in target_shares.items():
        summary[s] = qty * prices.get(s, 0.0) / capital
    return summary
