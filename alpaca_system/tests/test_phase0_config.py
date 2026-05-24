"""階段 0 測試：設定載入、多帳戶解析、缺金鑰報錯、免責聲明存在。"""
import textwrap

import pytest

from src.common.disclaimer import DISCLAIMER, DISCLAIMER_EN, DISCLAIMER_ZH
from src.config.accounts import (
    Account,
    MissingCredentialsError,
    load_accounts,
)


def _write_yaml(tmp_path, content: str):
    p = tmp_path / "accounts.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def test_disclaimer_present_and_nonempty():
    # 免責聲明常數存在且非空
    assert DISCLAIMER and DISCLAIMER.strip()
    assert DISCLAIMER == DISCLAIMER_ZH
    assert "投資建議" in DISCLAIMER_ZH
    assert "investment advice" in DISCLAIMER_EN.lower()


def test_load_single_account(tmp_path):
    p = _write_yaml(
        tmp_path,
        """
        accounts:
          - id: main
            env: paper
            strategy: nasdaq_momentum_top10
            key_env: ALPACA_MAIN_KEY
            secret_env: ALPACA_MAIN_SECRET
        """,
    )
    cfg = load_accounts(p)
    assert len(cfg.accounts) == 1
    acc = cfg.get("main")
    assert acc.is_paper is True
    assert acc.base_url.endswith("paper-api.alpaca.markets")
    assert acc.strategy == "nasdaq_momentum_top10"


def test_load_multiple_accounts(tmp_path):
    p = _write_yaml(
        tmp_path,
        """
        accounts:
          - id: main
            env: paper
            strategy: nasdaq_momentum_top10
            key_env: ALPACA_MAIN_KEY
            secret_env: ALPACA_MAIN_SECRET
          - id: aggressive
            env: live
            strategy: another_strategy
            key_env: ALPACA_AGG_KEY
            secret_env: ALPACA_AGG_SECRET
        """,
    )
    cfg = load_accounts(p)
    assert {a.id for a in cfg.accounts} == {"main", "aggressive"}
    assert cfg.get("aggressive").base_url.endswith("api.alpaca.markets")
    assert cfg.get("aggressive").is_paper is False


def test_duplicate_ids_rejected(tmp_path):
    p = _write_yaml(
        tmp_path,
        """
        accounts:
          - id: main
            env: paper
            strategy: s1
            key_env: K1
            secret_env: S1
          - id: main
            env: paper
            strategy: s2
            key_env: K2
            secret_env: S2
        """,
    )
    with pytest.raises(Exception):
        load_accounts(p)


def test_missing_credentials_raises(monkeypatch):
    monkeypatch.delenv("ALPACA_MAIN_KEY", raising=False)
    monkeypatch.delenv("ALPACA_MAIN_SECRET", raising=False)
    acc = Account(
        id="main",
        env="paper",
        strategy="s",
        key_env="ALPACA_MAIN_KEY",
        secret_env="ALPACA_MAIN_SECRET",
    )
    with pytest.raises(MissingCredentialsError) as exc:
        acc.resolve_credentials()
    assert "ALPACA_MAIN_KEY" in str(exc.value)


def test_resolve_credentials_ok(monkeypatch):
    monkeypatch.setenv("ALPACA_MAIN_KEY", "abc")
    monkeypatch.setenv("ALPACA_MAIN_SECRET", "xyz")
    acc = Account(
        id="main",
        env="paper",
        strategy="s",
        key_env="ALPACA_MAIN_KEY",
        secret_env="ALPACA_MAIN_SECRET",
    )
    assert acc.resolve_credentials() == ("abc", "xyz")


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_accounts(tmp_path / "nope.yaml")


def test_bundled_default_accounts_yaml_is_valid():
    # 倉庫內附的 accounts.yaml 必須能成功解析
    cfg = load_accounts()
    assert len(cfg.accounts) >= 1
