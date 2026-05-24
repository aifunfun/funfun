"""多帳戶設定載入。

從 accounts.yaml 讀取帳戶清單，並從環境變數解析 Alpaca API 金鑰
（金鑰絕不寫進設定檔，改用環境變數 / GitHub Secrets）。

每個帳戶同一時間只綁定一個策略；要更換策略只需改 accounts.yaml 的 strategy 欄位。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

# Alpaca 交易 API 端點
PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"

_DEFAULT_ACCOUNTS_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "accounts.yaml"
)


class MissingCredentialsError(RuntimeError):
    """環境變數中找不到帳戶所需的 API 金鑰時拋出。"""


class Account(BaseModel):
    """單一交易帳戶設定。"""

    id: str = Field(..., min_length=1)
    env: Literal["paper", "live"] = "paper"
    strategy: str = Field(..., min_length=1)
    key_env: str = Field(..., min_length=1)
    secret_env: str = Field(..., min_length=1)

    @field_validator("id", "strategy", "key_env", "secret_env")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("欄位不可為空白")
        return v

    @property
    def base_url(self) -> str:
        return PAPER_BASE_URL if self.env == "paper" else LIVE_BASE_URL

    @property
    def is_paper(self) -> bool:
        return self.env == "paper"

    def resolve_credentials(self) -> tuple[str, str]:
        """從環境變數取出 (api_key, api_secret)。

        缺少任一個就拋出明確錯誤，避免靜默用空金鑰連線。
        """
        key = os.environ.get(self.key_env)
        secret = os.environ.get(self.secret_env)
        missing = [
            name
            for name, val in ((self.key_env, key), (self.secret_env, secret))
            if not val
        ]
        if missing:
            raise MissingCredentialsError(
                f"帳戶 '{self.id}' 缺少環境變數: {', '.join(missing)}。"
                "請在環境變數或 GitHub Secrets 中設定。"
            )
        return key, secret  # type: ignore[return-value]


class AccountsConfig(BaseModel):
    accounts: list[Account] = Field(default_factory=list)

    @field_validator("accounts")
    @classmethod
    def _unique_ids(cls, accounts: list[Account]) -> list[Account]:
        ids = [a.id for a in accounts]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"帳戶 id 重複: {', '.join(sorted(dupes))}")
        return accounts

    def get(self, account_id: str) -> Account:
        for a in self.accounts:
            if a.id == account_id:
                return a
        raise KeyError(f"找不到帳戶 id: {account_id}")


def load_accounts(path: str | Path | None = None) -> AccountsConfig:
    """讀取並驗證 accounts.yaml。"""
    cfg_path = Path(path) if path else _DEFAULT_ACCOUNTS_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"找不到帳戶設定檔: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return AccountsConfig(**raw)
