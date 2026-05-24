"""再平衡觸發判斷 + 目標 vs 現況的買賣單 diff。

觸發條件（依需求）：
- 每月初（該月第一次執行）再平衡一次。
- 有新資金進來時再平衡一次。
- schedule 也支援 daily / none。

diff：比較目前持股與目標股數，產生買/賣清單；先賣後買以釋出現金；只用整數股。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

SideStr = Literal["buy", "sell"]

# 偵測新資金的最小金額門檻（避免價格小數誤判）
NEW_CASH_EPS = 1.0


@dataclass
class RebalanceState:
    """需在執行間持久化的狀態（存在帳戶層級的小檔案即可）。"""

    last_rebalance_date: date | None = None
    baseline_cash: float = 0.0  # 上次再平衡後記錄的現金基準


@dataclass
class OrderIntent:
    symbol: str
    qty: int
    side: SideStr


def is_new_month(today: date, last_rebalance_date: date | None) -> bool:
    if last_rebalance_date is None:
        return True
    return (today.year, today.month) != (
        last_rebalance_date.year,
        last_rebalance_date.month,
    )


def detect_new_cash(current_cash: float, baseline_cash: float) -> bool:
    """目前現金明顯高於基準 → 視為有新資金進來。"""
    return current_cash > baseline_cash + NEW_CASH_EPS


def should_rebalance(
    rebalance_cfg: dict,
    today: date,
    state: RebalanceState,
    current_cash: float,
) -> tuple[bool, str]:
    """回傳 (是否再平衡, 原因)。原因供報告/通知說明。"""
    schedule = rebalance_cfg.get("schedule", "none")

    if schedule == "daily":
        return True, "daily"

    if schedule == "monthly_first_trading_day" and is_new_month(
        today, state.last_rebalance_date
    ):
        return True, "monthly_first_trading_day"

    if rebalance_cfg.get("on_new_cash") and detect_new_cash(
        current_cash, state.baseline_cash
    ):
        return True, "new_cash"

    return False, "no_trigger"


def diff_orders(
    current_shares: dict[str, int], target_shares: dict[str, int]
) -> list[OrderIntent]:
    """比較現況與目標，產生買賣單。先賣（含出清不在目標內的股票）後買。"""
    sells: list[OrderIntent] = []
    buys: list[OrderIntent] = []

    all_symbols = set(current_shares) | set(target_shares)
    for symbol in sorted(all_symbols):
        cur = int(current_shares.get(symbol, 0))
        tgt = int(target_shares.get(symbol, 0))
        delta = tgt - cur
        if delta > 0:
            buys.append(OrderIntent(symbol, delta, "buy"))
        elif delta < 0:
            sells.append(OrderIntent(symbol, -delta, "sell"))
    return sells + buys
