"""實連煙霧測試（需設定 Paper 金鑰才會跑）。

用法（PowerShell）：
    $env:ALPACA_MAIN_KEY="..."; $env:ALPACA_MAIN_SECRET="..."
    python scripts/smoke_alpaca.py

會：讀帳戶現金、列持倉、查一檔報價。預設只讀取，不送單。
加 --place-test-order 才會送一張 1 股 AAPL 市價單並立刻嘗試取消（僅 Paper 建議）。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.brokers.alpaca_client import AlpacaClient  # noqa: E402
from src.config.accounts import load_accounts  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="main")
    ap.add_argument("--place-test-order", action="store_true")
    args = ap.parse_args()

    acc = load_accounts().get(args.account)
    print(f"帳戶 {acc.id} ({acc.env}) -> {acc.base_url}")
    client = AlpacaClient.from_account(acc)

    info = client.get_account()
    print(f"現金: {info.cash}  總資產: {info.equity}  買力: {info.buying_power}")

    positions = client.get_positions()
    print(f"持倉數: {len(positions)}")
    for p in positions:
        print(f"  {p.symbol}: {p.qty} 股, 未實現損益 {p.unrealized_plpc:.2%}")

    price = client.get_latest_price("AAPL")
    print(f"AAPL 最新成交價: {price}")

    if args.place_test_order:
        if not acc.is_paper:
            print("拒絕：--place-test-order 僅允許在 paper 帳戶執行。")
            return 1
        o = client.submit_market_order("AAPL", 1, "buy")
        print(f"已送出測試單: {o.id} 狀態 {o.status}")
        try:
            client.cancel_order(o.id)
            print("已嘗試取消測試單。")
        except Exception as e:  # noqa: BLE001
            print(f"取消失敗（可能已成交）: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
