"""階段 8 測試：儀表板資料整理純函式（含勾選對比、多帳戶選單）。"""
from src.config.accounts import AccountsConfig
from src.dashboard.view_data import (
    account_ids,
    build_drawdown_plot_data,
    build_nav_plot_data,
    holdings_rows,
    top10_rows,
)
from src.report.model import build_report_model


def _report():
    return build_report_model(
        account_id="main", as_of="2026-05-23", env="paper",
        strategy="s", cash=1000.0, equity=10000.0,
        holdings=[{"symbol": "AAPL", "qty": 10, "market_value": 1600.0,
                   "returns": {"1d": 0.01, "1w": None, "1m": 0.08},
                   "pe_ratio": 30.5}],
        top10=[{"rank": 1, "symbol": "NVDA", "score": 0.25}],
        next_day_candidates=[{"symbol": "NVDA", "score": 0.25}],
        watch_categories=[],
        nav_dates=["d1", "d2", "d3"],
        portfolio_equity_series=[9500, 9800, 10000],
        nasdaq_series=[18000, 18100, 18200],
        sp500_series=[5200, 5210, 5230],
    )


def test_nav_plot_shows_portfolio_always():
    data = build_nav_plot_data(_report(), show_nasdaq=False, show_sp500=False)
    assert "Portfolio" in data
    assert "NASDAQ" not in data
    assert "S&P 500" not in data


def test_nav_plot_checkboxes_add_benchmarks():
    data = build_nav_plot_data(_report(), show_nasdaq=True, show_sp500=True)
    assert set(data) >= {"Portfolio", "NASDAQ", "S&P 500", "dates"}
    assert data["NASDAQ"][0] == 100.0  # 已正規化


def test_nav_plot_toggle_only_nasdaq():
    data = build_nav_plot_data(_report(), show_nasdaq=True, show_sp500=False)
    assert "NASDAQ" in data and "S&P 500" not in data


def test_drawdown_plot_data_percent():
    data = build_drawdown_plot_data(_report(), show_nasdaq=True, show_sp500=False)
    assert "Portfolio" in data and "NASDAQ" in data
    # drawdown 第一點為 0
    assert data["Portfolio"][0] == 0.0


def test_holdings_rows_formats_returns():
    rows = holdings_rows(_report())
    assert rows[0]["股票"] == "AAPL"
    assert rows[0]["1日 %"] == "+1.00%"
    assert rows[0]["1週 %"] == "—"  # None -> 破折號
    assert rows[0]["本益比"] == 30.5


def test_top10_rows():
    rows = top10_rows(_report())
    assert rows[0]["股票"] == "NVDA"
    assert rows[0]["分數 %"] == "+25.00%"


def test_account_ids_for_selector():
    cfg = AccountsConfig(accounts=[
        {"id": "main", "env": "paper", "strategy": "s",
         "key_env": "K", "secret_env": "S"},
        {"id": "alt", "env": "live", "strategy": "s2",
         "key_env": "K2", "secret_env": "S2"},
    ])
    assert account_ids(cfg) == ["main", "alt"]
