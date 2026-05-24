"""把 Alpaca + yfinance 接成策略引擎需要的 DataAdapter。

引擎只認得 build_universe / get_closes 兩個方法（見 strategy/engine.py 的 Protocol）。
這層把真實資料源接上去；單元測試則用假 adapter。
"""
from __future__ import annotations

import pandas as pd

from src.brokers.alpaca_client import AlpacaClient
from src.data.fundamentals import get_fundamentals_batch
from src.data.market_data import get_daily_closes
from src.data.universe import build_nasdaq_universe


class AlpacaDataAdapter:
    def __init__(self, client: AlpacaClient, fundamentals_fn=None, lookback_days=40):
        self.client = client
        self.fundamentals_fn = fundamentals_fn or get_fundamentals_batch
        self.lookback_days = lookback_days

    def build_universe(self, source: str, rank_by: str, top_n: int) -> list[str]:
        # 目前 source 僅支援 nasdaq；rank_by 僅支援 market_cap
        return build_nasdaq_universe(top_n, fundamentals_fn=self.fundamentals_fn)

    def get_closes(self, symbol: str) -> pd.Series:
        return get_daily_closes(self.client.data_client, symbol, self.lookback_days)
