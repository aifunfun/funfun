"""Alpaca 交易連線層。

把 alpaca-py SDK 包成乾淨介面，回傳純資料物件（dataclass / dict），
讓系統其他部分不直接依賴 SDK 型別，也方便用 mock 做單元測試。

支援 paper / live（由 Account.env 決定端點）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from src.config.accounts import Account

OrderSideStr = Literal["buy", "sell"]


@dataclass
class AccountInfo:
    cash: float          # 現金水位
    equity: float        # 總資產（現金 + 持倉市值）
    buying_power: float  # 可用買力
    currency: str = "USD"


@dataclass
class Position:
    symbol: str
    qty: float                 # 持有股數
    avg_entry_price: float     # 平均成本
    market_value: float        # 目前市值
    current_price: float
    unrealized_pl: float       # 未實現損益（金額）
    unrealized_plpc: float     # 未實現損益（百分比，0.05 = 5%）


@dataclass
class OrderResult:
    id: str
    symbol: str
    qty: float
    side: str
    status: str


def _f(value: Any, default: float = 0.0) -> float:
    """SDK 欄位常是字串或 None，安全轉 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class AlpacaClient:
    """Alpaca 帳戶/下單/報價的薄包裝。

    可注入 trading_client / data_client 以利測試；
    正式使用請用 `AlpacaClient.from_account(account)`。
    """

    def __init__(self, trading_client: Any, data_client: Any | None = None):
        self._trading = trading_client
        self._data = data_client

    @classmethod
    def from_account(cls, account: Account) -> "AlpacaClient":
        # 延遲匯入 SDK，讓沒裝 alpaca-py 的環境仍能跑 mock 測試
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.trading.client import TradingClient

        key, secret = account.resolve_credentials()
        trading = TradingClient(key, secret, paper=account.is_paper)
        data = StockHistoricalDataClient(key, secret)
        return cls(trading, data)

    # ---- 帳戶 ----
    def get_account(self) -> AccountInfo:
        a = self._trading.get_account()
        return AccountInfo(
            cash=_f(getattr(a, "cash", None)),
            equity=_f(getattr(a, "equity", None)),
            buying_power=_f(getattr(a, "buying_power", None)),
            currency=getattr(a, "currency", "USD") or "USD",
        )

    def get_cash(self) -> float:
        return self.get_account().cash

    # ---- 持倉 ----
    def get_positions(self) -> list[Position]:
        raw = self._trading.get_all_positions()
        out: list[Position] = []
        for p in raw:
            out.append(
                Position(
                    symbol=getattr(p, "symbol", ""),
                    qty=_f(getattr(p, "qty", None)),
                    avg_entry_price=_f(getattr(p, "avg_entry_price", None)),
                    market_value=_f(getattr(p, "market_value", None)),
                    current_price=_f(getattr(p, "current_price", None)),
                    unrealized_pl=_f(getattr(p, "unrealized_pl", None)),
                    unrealized_plpc=_f(getattr(p, "unrealized_plpc", None)),
                )
            )
        return out

    @property
    def data_client(self) -> Any:
        return self._data

    # ---- 報價 ----
    def get_latest_price(self, symbol: str) -> float:
        return self.get_latest_prices([symbol]).get(symbol, 0.0)

    def get_latest_prices(self, symbols: list[str]) -> dict[str, float]:
        if not symbols:
            return {}
        from alpaca.data.requests import StockLatestTradeRequest

        req = StockLatestTradeRequest(symbol_or_symbols=symbols)
        trades = self._data.get_stock_latest_trade(req)
        return {sym: _f(getattr(t, "price", None)) for sym, t in trades.items()}

    # ---- 下單 ----
    def submit_market_order(
        self, symbol: str, qty: int, side: OrderSideStr
    ) -> OrderResult:
        """送出市價單（只支援整數股）。"""
        if qty <= 0:
            raise ValueError(f"下單股數必須為正整數，收到: {qty}")
        if qty != int(qty):
            raise ValueError(f"只支援整數股，收到: {qty}")

        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=symbol,
            qty=int(qty),
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
        o = self._trading.submit_order(req)
        return OrderResult(
            id=str(getattr(o, "id", "")),
            symbol=getattr(o, "symbol", symbol),
            qty=_f(getattr(o, "qty", qty)),
            side=str(getattr(getattr(o, "side", side), "value", side)),
            status=str(getattr(getattr(o, "status", ""), "value", "")),
        )

    def cancel_order(self, order_id: str) -> None:
        self._trading.cancel_order_by_id(order_id)

    def get_orders(self) -> list[OrderResult]:
        raw = self._trading.get_orders()
        return [
            OrderResult(
                id=str(getattr(o, "id", "")),
                symbol=getattr(o, "symbol", ""),
                qty=_f(getattr(o, "qty", None)),
                side=str(getattr(getattr(o, "side", ""), "value", "")),
                status=str(getattr(getattr(o, "status", ""), "value", "")),
            )
            for o in raw
        ]
