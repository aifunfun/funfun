"""即時交易通知。

把成交/下單事件格式化成白話訊息（含免責聲明），並透過可插拔的 sink 送出。
預設用 ConsoleNotifier（印到 log）；正式可換成 Email/其他通知（重用階段 7 的寄信）。
"""
from __future__ import annotations

from typing import Protocol

from src.common.disclaimer import DISCLAIMER


class ExecutionResultLike(Protocol):
    symbol: str
    qty: int
    side: str
    status: str
    detail: str


_SIDE_ZH = {"buy": "買進", "sell": "賣出"}


def format_trade_message(account_id: str, result: ExecutionResultLike) -> str:
    """單筆交易的白話通知文字（含免責）。"""
    action = _SIDE_ZH.get(result.side, result.side)
    head = f"[{account_id}] {action} {result.symbol} {result.qty} 股 — 狀態: {result.status}"
    if result.detail:
        head += f"（{result.detail}）"
    return f"{head}\n{DISCLAIMER}"


def format_batch_message(account_id: str, results: list[ExecutionResultLike]) -> str:
    """一次再平衡的多筆交易彙總通知（含免責）。"""
    if not results:
        return f"[{account_id}] 本次無交易。\n{DISCLAIMER}"
    lines = [f"[{account_id}] 本次交易共 {len(results)} 筆："]
    for r in results:
        action = _SIDE_ZH.get(r.side, r.side)
        lines.append(f"  • {action} {r.symbol} {r.qty} 股 — {r.status}")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


class Notifier(Protocol):
    def notify(self, subject: str, body: str) -> None: ...


class ConsoleNotifier:
    """最簡單的通知：印出來（CI log 會記錄）。"""

    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def notify(self, subject: str, body: str) -> None:
        self.sent.append((subject, body))
        print(f"=== {subject} ===\n{body}\n")
