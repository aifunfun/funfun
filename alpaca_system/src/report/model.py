"""報告 Model：把各路資料組成「一份 JSON 報告」。

Model/View 分離：這裡只產生資料（dict / JSON），不負責畫面。
Email 與 Streamlit 都讀這份 JSON。所有報告一律附免責聲明。

build_report_model 不做任何網路呼叫，輸入皆為已取得的資料，方便測試與重現。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.common.disclaimer import DISCLAIMER
from src.report.metrics import compute_drawdown, max_drawdown, normalize_to_base

REPORT_SCHEMA_VERSION = 1

REQUIRED_KEYS = {
    "schema_version", "as_of", "account_id", "cash", "equity",
    "holdings", "top10", "next_day_candidates", "watch_categories",
    "nav", "drawdown", "rebalance", "disclaimer",
}


def build_report_model(
    *,
    account_id: str,
    as_of: str,
    env: str,
    strategy: str,
    cash: float,
    equity: float,
    holdings: list[dict[str, Any]],
    top10: list[dict[str, Any]],
    next_day_candidates: list[dict[str, Any]],
    watch_categories: list[dict[str, Any]],
    nav_dates: list[str],
    portfolio_equity_series: list[float],
    nasdaq_series: list[float] | None = None,
    sp500_series: list[float] | None = None,
    rebalance: dict[str, Any] | None = None,
    trades: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """組出標準化的報告 dict。

    NAV 與大盤(NASDAQ/SP500)皆正規化到 100，方便疊圖比較與勾選。
    """
    nav_portfolio = normalize_to_base(portfolio_equity_series, 100.0)
    nav_nasdaq = normalize_to_base(nasdaq_series, 100.0) if nasdaq_series else []
    nav_sp500 = normalize_to_base(sp500_series, 100.0) if sp500_series else []

    dd_portfolio = compute_drawdown(nav_portfolio)
    dd_nasdaq = compute_drawdown(nav_nasdaq) if nav_nasdaq else []
    dd_sp500 = compute_drawdown(nav_sp500) if nav_sp500 else []

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "as_of": as_of,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "account_id": account_id,
        "env": env,
        "strategy": strategy,
        "cash": round(float(cash), 2),
        "equity": round(float(equity), 2),
        "holdings": holdings,
        "top10": top10,
        # 明確標示：這是依因子排名的「研究參考清單」，不是預測，也不是投資建議
        "next_day_candidates": {
            "note": "依動能等因子排名的研究參考清單，非股價預測，不構成投資建議。",
            "items": next_day_candidates,
        },
        "watch_categories": watch_categories,
        "nav": {
            "dates": nav_dates,
            "portfolio": nav_portfolio,
            "nasdaq": nav_nasdaq,
            "sp500": nav_sp500,
        },
        "drawdown": {
            "dates": nav_dates,
            "portfolio": dd_portfolio,
            "nasdaq": dd_nasdaq,
            "sp500": dd_sp500,
            "portfolio_max_drawdown": max_drawdown(nav_portfolio),
        },
        "rebalance": rebalance or {"triggered": False, "reason": "no_trigger"},
        "trades": trades or [],
        "disclaimer": DISCLAIMER,
    }


def validate_report(report: dict) -> None:
    """確認報告含所有必填欄位與非空免責聲明。"""
    missing = REQUIRED_KEYS - set(report.keys())
    if missing:
        raise ValueError(f"報告缺少必填欄位: {', '.join(sorted(missing))}")
    if not report.get("disclaimer", "").strip():
        raise ValueError("報告必須包含免責聲明。")
