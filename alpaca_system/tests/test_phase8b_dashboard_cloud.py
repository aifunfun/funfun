"""測試：儀表板不依賴本機與 accounts.yaml，可由 reports/ 與 REPORTS_DIR 驅動。

對應需求：dashboard 不綁本機電腦、隨時可用（部署到雲端讀 repo 內報告）。
"""
import importlib.util
import sys
import types
from pathlib import Path

from src.dashboard.view_data import available_accounts
from src.report import store
from src.report.model import build_report_model


def _make_report(account_id="main", as_of="2026-05-23"):
    return build_report_model(
        account_id=account_id, as_of=as_of, env="paper", strategy="s",
        cash=1000.0, equity=10000.0,
        holdings=[{"symbol": "AAPL", "qty": 10,
                   "returns": {"1d": 0.01, "1w": 0.03, "1m": 0.08}, "pe_ratio": 30.5}],
        top10=[{"rank": 1, "symbol": "NVDA", "score": 0.25}],
        next_day_candidates=[{"symbol": "NVDA", "score": 0.25}],
        watch_categories=[],
        nav_dates=["2026-05-21", "2026-05-22", "2026-05-23"],
        portfolio_equity_series=[9500, 9800, 10000],
        nasdaq_series=[18000, 18100, 18200],
        sp500_series=[5200, 5210, 5230],
    )


# ---- REPORTS_DIR 環境變數覆寫 ----
def test_reports_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path))
    assert store.default_root() == tmp_path
    # 不傳 root，應寫到 REPORTS_DIR 指定的位置
    store.save_report(_make_report())
    assert (tmp_path / "main" / "2026-05-23.json").exists()
    assert store.list_report_dates("main") == ["2026-05-23"]


def test_default_root_falls_back_to_repo(monkeypatch):
    monkeypatch.delenv("REPORTS_DIR", raising=False)
    assert store.default_root().name == "reports"


# ---- list_accounts 掃資料夾（不靠 accounts.yaml）----
def test_list_accounts_scans_report_dirs(tmp_path):
    store.save_report(_make_report("main"), root=tmp_path)
    store.save_report(_make_report("alt"), root=tmp_path)
    (tmp_path / "empty_dir").mkdir()  # 沒有 json 的資料夾不算
    assert store.list_accounts(root=tmp_path) == ["alt", "main"]


def test_list_accounts_empty_when_no_reports(tmp_path):
    assert store.list_accounts(root=tmp_path) == []


# ---- available_accounts 合併去重排序 ----
def test_available_accounts_merge_dedup_sort():
    assert available_accounts(["main"], ["main", "alt"]) == ["alt", "main"]
    assert available_accounts(["b"], None) == ["b"]
    assert available_accounts([], ["x"]) == ["x"]


# ---- 整合：缺 accounts.yaml 也能跑（帳戶清單來自 reports/）----
def test_dashboard_runs_without_accounts_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path))
    store.save_report(_make_report("main"), root=tmp_path)

    # 模擬「沒有 accounts.yaml」：讓 load_accounts 失敗
    import src.config.accounts as acc_mod
    monkeypatch.setattr(
        acc_mod, "load_accounts",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("no config")),
    )

    # 用假的 streamlit 取代，避免需要伺服器
    st = types.ModuleType("streamlit")
    calls = []

    class Col:
        def metric(self, *a, **k):
            calls.append(("metric", a))

    def rec(name):
        def f(*a, **k):
            calls.append((name, a[:1]))
        return f

    for n in ["set_page_config", "title", "subheader", "line_chart", "dataframe",
              "write", "caption", "markdown", "divider", "warning", "error"]:
        setattr(st, n, rec(n))
    st.columns = lambda n: (Col(), Col(), Col())

    class SB:
        def selectbox(self, label, opts):
            return opts[0]

        def checkbox(self, label, value=False):
            return True

    st.sidebar = SB()
    monkeypatch.setitem(sys.modules, "streamlit", st)

    app_path = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "app.py"
    spec = importlib.util.spec_from_file_location("dash_app_cloud", app_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.main()

    # 有畫出 NAV / 回撤線圖 => 成功用 reports/ 的帳戶跑完，未依賴 accounts.yaml
    assert len([c for c in calls if c[0] == "line_chart"]) == 2
    assert not any(c[0] == "warning" for c in calls)
