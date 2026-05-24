"""再平衡狀態的持久化（每帳戶一個小 JSON）。

存於 reports/<account_id>/_state.json，記錄上次再平衡日期與現金基準，
讓「月初再平衡」「新資金再平衡」能跨次執行判斷。
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.portfolio.rebalance import RebalanceState

_DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "reports"


def _state_path(account_id: str, root: Path) -> Path:
    return root / account_id / "_state.json"


def load_state(account_id: str, root: str | Path | None = None) -> RebalanceState:
    base = Path(root) if root else _DEFAULT_ROOT
    path = _state_path(account_id, base)
    if not path.exists():
        return RebalanceState()
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    last = raw.get("last_rebalance_date")
    return RebalanceState(
        last_rebalance_date=date.fromisoformat(last) if last else None,
        baseline_cash=float(raw.get("baseline_cash", 0.0)),
    )


def save_state(
    account_id: str, state: RebalanceState, root: str | Path | None = None
) -> Path:
    base = Path(root) if root else _DEFAULT_ROOT
    path = _state_path(account_id, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = {
        "last_rebalance_date": (
            state.last_rebalance_date.isoformat()
            if state.last_rebalance_date
            else None
        ),
        "baseline_cash": state.baseline_cash,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    return path
