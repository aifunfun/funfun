"""Email 視圖：把報告 JSON 渲染成白話、視覺化的 HTML，並產生 NAV/回撤對比圖。

Model/View 分離：本檔只讀報告 dict，不做任何資料運算或網路呼叫。
圖表用 matplotlib（Agg 後端，免顯示器），畫出投組 vs NASDAQ vs SP500。
"""
from __future__ import annotations

import io
from typing import Any

import matplotlib

matplotlib.use("Agg")  # 無 GUI 環境也能產圖
import matplotlib.pyplot as plt  # noqa: E402


def _pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x * 100:+.2f}%"


def render_nav_chart_png(report: dict[str, Any]) -> bytes:
    """畫 NAV 對比圖（投組 / NASDAQ / SP500，皆正規化到 100）回傳 PNG bytes。"""
    nav = report.get("nav", {})
    dates = nav.get("dates", [])
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)

    # 圖內標籤用英文：避免 matplotlib 預設字型缺中文字而顯示成方框
    if nav.get("portfolio"):
        ax1.plot(dates, nav["portfolio"], label="Portfolio", linewidth=2)
    if nav.get("nasdaq"):
        ax1.plot(dates, nav["nasdaq"], label="NASDAQ", linestyle="--")
    if nav.get("sp500"):
        ax1.plot(dates, nav["sp500"], label="S&P 500", linestyle=":")
    ax1.set_title("NAV (base = 100)")
    ax1.legend(loc="best", fontsize=8)
    ax1.grid(True, alpha=0.3)

    dd = report.get("drawdown", {})
    if dd.get("portfolio"):
        ax2.plot(dates, [d * 100 for d in dd["portfolio"]], label="Portfolio", linewidth=2)
    if dd.get("nasdaq"):
        ax2.plot(dates, [d * 100 for d in dd["nasdaq"]], label="NASDAQ", linestyle="--")
    if dd.get("sp500"):
        ax2.plot(dates, [d * 100 for d in dd["sp500"]], label="S&P 500", linestyle=":")
    ax2.set_title("Drawdown (%)")
    ax2.legend(loc="best", fontsize=8)
    ax2.grid(True, alpha=0.3)

    if len(dates) > 8:
        for ax in (ax1, ax2):
            ax.set_xticks(ax.get_xticks()[:: max(1, len(dates) // 8)])
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    return buf.getvalue()


def render_html(report: dict[str, Any], chart_cid: str = "navchart") -> str:
    """把報告渲染成 HTML（圖以 cid 內嵌）。"""
    a = report
    holdings_rows = "".join(
        f"<tr><td>{h['symbol']}</td><td>{h.get('qty','')}</td>"
        f"<td>{_pct(h.get('returns',{}).get('1d'))}</td>"
        f"<td>{_pct(h.get('returns',{}).get('1w'))}</td>"
        f"<td>{_pct(h.get('returns',{}).get('1m'))}</td>"
        f"<td>{h.get('pe_ratio','—')}</td></tr>"
        for h in a.get("holdings", [])
    )

    top10_rows = "".join(
        f"<tr><td>{t.get('rank','')}</td><td>{t['symbol']}</td>"
        f"<td>{_pct(t.get('score'))}</td></tr>"
        for t in a.get("top10", [])
    )

    cand = a.get("next_day_candidates", {})
    cand_items = "".join(f"<li>{c['symbol']}（{_pct(c.get('score'))}）</li>"
                         for c in cand.get("items", []))

    cat_html = ""
    for cat in a.get("watch_categories", []):
        rows = "".join(
            f"<li>{s['symbol']} — 本益比 {s.get('pe_ratio','—')}</li>"
            for s in cat.get("symbols", [])
        )
        cat_html += f"<h3>{cat['name']}</h3><ul>{rows}</ul>"

    return f"""<html><body style="font-family:Arial,'Microsoft JhengHei',sans-serif;color:#222">
<h2>每日投資日報 — {a['account_id']}（{a.get('env','')}）</h2>
<p>日期：{a['as_of']}　策略：{a.get('strategy','')}</p>
<p><b>現金水位：</b>${a['cash']:,.2f}　<b>總資產：</b>${a['equity']:,.2f}</p>
<p><b>再平衡：</b>{'有' if a.get('rebalance',{}).get('triggered') else '無'}
（{a.get('rebalance',{}).get('reason','')}）</p>

<h3>淨值與回撤對比</h3>
<img src="cid:{chart_cid}" alt="NAV chart" style="max-width:100%"/>

<h3>持倉與報酬</h3>
<table border="1" cellpadding="5" cellspacing="0">
<tr><th>股票</th><th>股數</th><th>1日</th><th>1週</th><th>1月</th><th>本益比</th></tr>
{holdings_rows or '<tr><td colspan=6>目前無持倉</td></tr>'}
</table>

<h3>今日最強前十（依因子排名）</h3>
<table border="1" cellpadding="5" cellspacing="0">
<tr><th>名次</th><th>股票</th><th>分數</th></tr>{top10_rows}
</table>

<h3>隔日研究參考清單</h3>
<p style="color:#a00">{cand.get('note','')}</p>
<ul>{cand_items}</ul>

<h3>關注類別</h3>
{cat_html}

<hr/>
<p style="color:#888;font-size:12px">{a.get('disclaimer','')}</p>
</body></html>"""
