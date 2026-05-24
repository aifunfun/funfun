"""讀取關注類別清單（三大類別股票）。"""
from __future__ import annotations

from pathlib import Path

import yaml

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "watchlist.yaml"


def load_watchlist(path: str | Path | None = None) -> list[dict]:
    """回傳 [{name, symbols:[...]}, ...]。檔案不存在時回空清單。"""
    p = Path(path) if path else _DEFAULT_PATH
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return raw.get("categories", [])
