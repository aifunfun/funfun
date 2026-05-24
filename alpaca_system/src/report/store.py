"""歷史報告儲存：把報告 JSON 存成檔案，供使用者回查任一天。

路徑：<reports_root>/<account_id>/<YYYY-MM-DD>.json

reports_root 解析順序（讓儀表板能部署到雲端、不綁本機）：
1. 函式傳入的 root 參數
2. 環境變數 REPORTS_DIR（雲端部署時可指定）
3. 預設 repo 內的 alpaca_system/reports/（Streamlit Cloud 會讀 GitHub repo 內這份）
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_REPO_REPORTS = Path(__file__).resolve().parents[2] / "reports"


def default_root() -> Path:
    """目前生效的報告根目錄（含 REPORTS_DIR 環境變數覆寫）。"""
    env = os.environ.get("REPORTS_DIR")
    return Path(env) if env else _REPO_REPORTS


def _resolve_root(root: str | Path | None) -> Path:
    return Path(root) if root else default_root()


def _account_dir(account_id: str, root: Path) -> Path:
    return root / account_id


def save_report(report: dict[str, Any], root: str | Path | None = None) -> Path:
    """存報告，檔名用 report['as_of']。"""
    base = _resolve_root(root)
    account_id = report["account_id"]
    as_of = report["as_of"]
    d = _account_dir(account_id, base)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{as_of}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def load_report(
    account_id: str, as_of: str, root: str | Path | None = None
) -> dict[str, Any]:
    base = _resolve_root(root)
    path = _account_dir(account_id, base) / f"{as_of}.json"
    if not path.exists():
        raise FileNotFoundError(f"找不到報告: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_report_dates(account_id: str, root: str | Path | None = None) -> list[str]:
    """回傳該帳戶所有報告日期（由新到舊）。"""
    base = _resolve_root(root)
    d = _account_dir(account_id, base)
    if not d.exists():
        return []
    dates = [p.stem for p in d.glob("*.json")]
    return sorted(dates, reverse=True)


def list_accounts(root: str | Path | None = None) -> list[str]:
    """掃描報告根目錄，列出有報告的帳戶（不依賴 accounts.yaml）。

    讓儀表板只靠 reports/ 資料夾就能運作，部署到雲端時不需要設定檔。
    """
    base = _resolve_root(root)
    if not base.exists():
        return []
    accounts = [
        p.name
        for p in base.iterdir()
        if p.is_dir() and any(p.glob("*.json"))
    ]
    return sorted(accounts)


def load_latest(
    account_id: str, root: str | Path | None = None
) -> dict[str, Any] | None:
    dates = list_report_dates(account_id, root)
    if not dates:
        return None
    return load_report(account_id, dates[0], root)
