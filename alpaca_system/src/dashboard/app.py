"""Streamlit 儀表板（View）。

執行：
    cd alpaca_system
    streamlit run src/dashboard/app.py

讀「歷史報告 JSON」呈現：現金水位、持倉清單、各股 1日/1週/1月報酬、
今日最強前十、NAV 與回撤（可勾選 NASDAQ / SP500 對比）、關注類別、本益比。
支援多帳戶切換。所有畫面附免責聲明。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 在匯入 pandas/numpy 前限制 OpenBLAS 執行緒，避免部分環境記憶體配置失敗
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from src.dashboard.view_data import (  # noqa: E402
    available_accounts,
    build_drawdown_plot_data,
    build_nav_plot_data,
    holdings_rows,
    top10_rows,
)
from src.report.store import (  # noqa: E402
    list_accounts,
    list_report_dates,
    load_report,
)


def _line_df(series: dict[str, list]) -> pd.DataFrame:
    dates = series.pop("dates", [])
    return pd.DataFrame(series, index=dates)


def main() -> None:
    st.set_page_config(page_title="美股自動交易儀表板", layout="wide")
    st.title("美股自動交易儀表板")

    # 帳戶清單以「有報告的帳戶」為主（掃 reports/），不依賴 accounts.yaml；
    # 若 accounts.yaml 存在則一併納入，但缺檔也能正常運作（適合雲端部署）。
    report_accounts = list_accounts()
    configured: list[str] = []
    try:
        from src.config.accounts import load_accounts

        configured = [a.id for a in load_accounts().accounts]
    except Exception:  # noqa: BLE001 — 設定檔缺失不影響儀表板
        configured = []

    ids = available_accounts(report_accounts, configured)
    if not ids:
        st.warning("尚無任何報告。請先執行報告產生流程（scripts/run_report.py）。")
        return

    account_id = st.sidebar.selectbox("帳戶", ids)
    dates = list_report_dates(account_id)
    if not dates:
        st.warning(f"帳戶 {account_id} 尚無報告。請先執行報告產生流程。")
        return
    as_of = st.sidebar.selectbox("報告日期", dates)
    show_nasdaq = st.sidebar.checkbox("對比 NASDAQ", value=True)
    show_sp500 = st.sidebar.checkbox("對比 S&P 500", value=True)

    report = load_report(account_id, as_of)

    c1, c2, c3 = st.columns(3)
    c1.metric("現金水位", f"${report['cash']:,.2f}")
    c2.metric("總資產", f"${report['equity']:,.2f}")
    reb = report.get("rebalance", {})
    c3.metric("今日再平衡", "是" if reb.get("triggered") else "否", reb.get("reason", ""))

    st.subheader("NAV 淨值對比（起點 = 100）")
    st.line_chart(_line_df(build_nav_plot_data(report, show_nasdaq, show_sp500)))

    st.subheader("回撤 Drawdown (%)")
    st.line_chart(_line_df(build_drawdown_plot_data(report, show_nasdaq, show_sp500)))

    st.subheader("持倉與報酬（1日 / 1週 / 1月）")
    st.dataframe(pd.DataFrame(holdings_rows(report)), use_container_width=True)

    st.subheader("今日最強前十（依因子排名）")
    st.dataframe(pd.DataFrame(top10_rows(report)), use_container_width=True)

    cand = report.get("next_day_candidates", {})
    st.subheader("隔日研究參考清單")
    st.caption(cand.get("note", ""))
    st.write([c.get("symbol") for c in cand.get("items", [])])

    st.subheader("關注類別")
    for cat in report.get("watch_categories", []):
        st.markdown(f"**{cat['name']}**")
        st.dataframe(pd.DataFrame(cat.get("symbols", [])), use_container_width=True)

    st.divider()
    st.caption(report.get("disclaimer", ""))


if __name__ == "__main__":
    main()
