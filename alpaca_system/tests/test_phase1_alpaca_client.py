"""階段 1 測試：以 mock 驗證 Alpaca 連線層的資料正規化與下單防呆。

不需要真實連線；實連煙霧測試見 scripts/smoke_alpaca.py（需設定金鑰才跑）。
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.brokers.alpaca_client import AccountInfo, AlpacaClient, Position


def test_get_account_normalizes_strings():
    trading = MagicMock()
    trading.get_account.return_value = SimpleNamespace(
        cash="10000.50", equity="12345.00", buying_power="20000", currency="USD"
    )
    client = AlpacaClient(trading)
    acc = client.get_account()
    assert isinstance(acc, AccountInfo)
    assert acc.cash == 10000.50
    assert acc.equity == 12345.0
    assert acc.buying_power == 20000.0
    assert client.get_cash() == 10000.50


def test_get_positions_maps_fields():
    trading = MagicMock()
    trading.get_all_positions.return_value = [
        SimpleNamespace(
            symbol="AAPL",
            qty="10",
            avg_entry_price="150",
            market_value="1600",
            current_price="160",
            unrealized_pl="100",
            unrealized_plpc="0.0667",
        )
    ]
    client = AlpacaClient(trading)
    positions = client.get_positions()
    assert len(positions) == 1
    p = positions[0]
    assert isinstance(p, Position)
    assert p.symbol == "AAPL"
    assert p.qty == 10
    assert p.unrealized_plpc == pytest.approx(0.0667)


def _stub_data_requests(monkeypatch):
    import sys

    fake = SimpleNamespace(
        StockLatestTradeRequest=lambda **kw: SimpleNamespace(**kw)
    )
    monkeypatch.setitem(sys.modules, "alpaca.data.requests", fake)


def test_get_latest_prices(monkeypatch):
    _stub_data_requests(monkeypatch)
    data = MagicMock()
    data.get_stock_latest_trade.return_value = {
        "AAPL": SimpleNamespace(price="160.0"),
        "MSFT": SimpleNamespace(price="420.5"),
    }
    client = AlpacaClient(MagicMock(), data_client=data)
    prices = client.get_latest_prices(["AAPL", "MSFT"])
    assert prices == {"AAPL": 160.0, "MSFT": 420.5}
    assert client.get_latest_price("AAPL") == 160.0


def test_get_latest_prices_empty_symbols_returns_empty():
    client = AlpacaClient(MagicMock(), data_client=MagicMock())
    assert client.get_latest_prices([]) == {}


def test_submit_order_rejects_non_positive_qty():
    client = AlpacaClient(MagicMock())
    with pytest.raises(ValueError):
        client.submit_market_order("AAPL", 0, "buy")
    with pytest.raises(ValueError):
        client.submit_market_order("AAPL", -5, "sell")


def test_submit_order_calls_sdk_and_returns_result(monkeypatch):
    # 模擬 SDK submit_order 回傳
    trading = MagicMock()
    trading.submit_order.return_value = SimpleNamespace(
        id="order-123",
        symbol="AAPL",
        qty="5",
        side=SimpleNamespace(value="buy"),
        status=SimpleNamespace(value="accepted"),
    )
    # 攔截 alpaca SDK 匯入，避免需要安裝套件
    import sys

    fake_enums = SimpleNamespace(
        OrderSide=SimpleNamespace(BUY="buy", SELL="sell"),
        TimeInForce=SimpleNamespace(DAY="day"),
    )
    fake_requests = SimpleNamespace(
        MarketOrderRequest=lambda **kw: SimpleNamespace(**kw)
    )
    monkeypatch.setitem(sys.modules, "alpaca.trading.enums", fake_enums)
    monkeypatch.setitem(sys.modules, "alpaca.trading.requests", fake_requests)

    client = AlpacaClient(trading)
    result = client.submit_market_order("AAPL", 5, "buy")
    assert result.id == "order-123"
    assert result.symbol == "AAPL"
    assert result.qty == 5
    assert result.side == "buy"
    assert result.status == "accepted"
    trading.submit_order.assert_called_once()


def test_cancel_order_delegates():
    trading = MagicMock()
    client = AlpacaClient(trading)
    client.cancel_order("abc")
    trading.cancel_order_by_id.assert_called_once_with("abc")
