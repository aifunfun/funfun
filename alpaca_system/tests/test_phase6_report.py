"""階段 6 測試：metrics 數學、報告必填欄位+免責、歷史儲存 round-trip。"""
import pytest

from src.common.disclaimer import DISCLAIMER
from src.report.metrics import (
    compute_drawdown,
    compute_nav_series,
    max_drawdown,
    normalize_to_base,
)
from src.report.model import build_report_model, validate_report
from src.report.store import (
    list_report_dates,
    load_latest,
    load_report,
    save_report,
)


# ---- metrics ----
def test_normalize_to_base():
    nav = compute_nav_series([200, 220, 180], base=100.0)
    assert nav == pytest.approx([100.0, 110.0, 90.0])


def test_normalize_handles_zero_start():
    assert normalize_to_base([0, 1, 2], 100.0) == [100.0, 100.0, 100.0]


def test_drawdown_math():
    nav = [100, 110, 99, 120]  # 高點110後跌到99 -> -10%
    dd = compute_drawdown(nav)
    assert dd[0] == 0.0
    assert dd[1] == 0.0
    assert dd[2] == pytest.approx(99 / 110 - 1)
    assert dd[3] == 0.0  # 創新高
    assert max_drawdown(nav) == pytest.approx(99 / 110 - 1)


# ---- report model ----
def _sample_model():
    return build_report_model(
        account_id="main",
        as_of="2026-05-23",
        env="paper",
        strategy="nasdaq_momentum_top10",
        cash=1234.56,
        equity=10000.0,
        holdings=[
            {"symbol": "AAPL", "qty": 10, "market_value": 1600.0,
             "returns": {"1d": 0.01, "1w": 0.03, "1m": 0.08}, "pe_ratio": 30.5}
        ],
        top10=[{"rank": 1, "symbol": "NVDA", "score": 0.25}],
        next_day_candidates=[{"symbol": "NVDA", "score": 0.25}],
        watch_categories=[
            {"name": "半導體", "symbols": [{"symbol": "NVDA", "pe_ratio": 60.0}]}
        ],
        nav_dates=["2026-05-21", "2026-05-22", "2026-05-23"],
        portfolio_equity_series=[9500, 9800, 10000],
        nasdaq_series=[18000, 18100, 18200],
        sp500_series=[5200, 5210, 5230],
        rebalance={"triggered": True, "reason": "monthly_first_trading_day"},
    )


def test_report_has_required_keys_and_disclaimer():
    report = _sample_model()
    validate_report(report)  # 不應拋錯
    assert report["disclaimer"] == DISCLAIMER
    # NAV 與大盤皆正規化到 100 起點
    assert report["nav"]["portfolio"][0] == 100.0
    assert report["nav"]["nasdaq"][0] == 100.0
    assert report["nav"]["sp500"][0] == 100.0


def test_next_day_labeled_as_research_not_prediction():
    report = _sample_model()
    assert "預測" not in report["next_day_candidates"]["note"] or "非股價預測" in \
        report["next_day_candidates"]["note"]
    assert "不構成投資建議" in report["next_day_candidates"]["note"]


def test_validate_report_catches_missing_field():
    report = _sample_model()
    del report["cash"]
    with pytest.raises(ValueError):
        validate_report(report)


def test_validate_report_catches_empty_disclaimer():
    report = _sample_model()
    report["disclaimer"] = "  "
    with pytest.raises(ValueError):
        validate_report(report)


# ---- store round-trip ----
def test_save_and_load_round_trip(tmp_path):
    report = _sample_model()
    path = save_report(report, root=tmp_path)
    assert path.exists()
    loaded = load_report("main", "2026-05-23", root=tmp_path)
    assert loaded == report


def test_list_and_latest(tmp_path):
    r1 = _sample_model()
    r2 = _sample_model()
    r2["as_of"] = "2026-05-24"
    save_report(r1, root=tmp_path)
    save_report(r2, root=tmp_path)
    dates = list_report_dates("main", root=tmp_path)
    assert dates == ["2026-05-24", "2026-05-23"]
    assert load_latest("main", root=tmp_path)["as_of"] == "2026-05-24"


def test_latest_none_when_empty(tmp_path):
    assert load_latest("ghost", root=tmp_path) is None
