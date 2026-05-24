"""儀表板的「資料整理」純函式（與 Streamlit UI 分離，方便測試）。

Model/View 分離：這裡只把報告 JSON 整理成方便畫圖/列表的結構，
app.py 負責用 Streamlit 把它們畫出來。
"""
from __future__ import annotations

from typing import Any


def build_nav_plot_data(
    report: dict[str, Any], show_nasdaq: bool, show_sp500: bool
) -> dict[str, list]:
    """依勾選狀態回傳要疊在 NAV 圖上的序列。

    投組一定顯示；NASDAQ / SP500 可由勾選決定（對應需求：可勾選對比）。
    """
    nav = report.get("nav", {})
    series: dict[str, list] = {"dates": nav.get("dates", [])}
    series["Portfolio"] = nav.get("portfolio", [])
    if show_nasdaq and nav.get("nasdaq"):
        series["NASDAQ"] = nav["nasdaq"]
    if show_sp500 and nav.get("sp500"):
        series["S&P 500"] = nav["sp500"]
    return series


def build_drawdown_plot_data(
    report: dict[str, Any], show_nasdaq: bool, show_sp500: bool
) -> dict[str, list]:
    dd = report.get("drawdown", {})
    series: dict[str, list] = {"dates": dd.get("dates", [])}
    series["Portfolio"] = [d * 100 for d in dd.get("portfolio", [])]
    if show_nasdaq and dd.get("nasdaq"):
        series["NASDAQ"] = [d * 100 for d in dd["nasdaq"]]
    if show_sp500 and dd.get("sp500"):
        series["S&P 500"] = [d * 100 for d in dd["sp500"]]
    return series


def holdings_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """整理持倉清單成表格列（含 1日/1週/1月報酬與本益比）。"""
    rows = []
    for h in report.get("holdings", []):
        r = h.get("returns", {})
        rows.append(
            {
                "股票": h.get("symbol"),
                "股數": h.get("qty"),
                "市值": h.get("market_value"),
                "1日 %": _pct(r.get("1d")),
                "1週 %": _pct(r.get("1w")),
                "1月 %": _pct(r.get("1m")),
                "本益比": h.get("pe_ratio", "—"),
            }
        )
    return rows


def top10_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"名次": t.get("rank"), "股票": t.get("symbol"), "分數 %": _pct(t.get("score"))}
        for t in report.get("top10", [])
    ]


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:+.2f}%"


def account_ids(accounts_config) -> list[str]:
    """從帳戶設定取出可選帳戶 id 清單（給多帳戶切換選單）。"""
    return [a.id for a in accounts_config.accounts]


def available_accounts(report_accounts, configured_accounts=None) -> list[str]:
    """儀表板要顯示的帳戶清單。

    以「有報告的帳戶」(report_accounts) 為主，可選擇性併入設定檔帳戶
    (configured_accounts)。這樣儀表板只靠 reports/ 就能運作，不必依賴 accounts.yaml。
    """
    merged = list(dict.fromkeys(list(report_accounts) + list(configured_accounts or [])))
    return sorted(merged)
