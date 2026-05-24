# PROJECT — Alpaca 美股全自動交易 + 報告 + 儀表板系統

> 這份文件是「專案記憶」：讓未來的你或其他開發者**快速看懂整個專案**並接手開發。

## 一句話定位
串接 Alpaca 的美股系統：每交易日自動下單、算盈虧、產日報、寄 Email、Streamlit 視覺化。
**定位是資訊整理／追蹤／視覺化／通知工具，不代操、不保證獲利。**

## 重要原則（務必遵守）
- 所有排名、績效、隔日清單、Email、通知都要附免責聲明（`src/common/disclaimer.py` 的 `DISCLAIMER`）。
- 先用 **Paper 模擬盤**，確認無誤再切真實盤（`accounts.yaml` 的 `env`）。
- 新增交易策略**只加 JSON**（`strategies/*.json`）。只有要「全新一種訊號積木」時，才需在 `src/strategy/rules.py` 擴充並註冊。
- 報告 **Model/View 分離**：報告是 JSON（`report/model.py`），Email（`report/email_view.py`）與 Dashboard（`dashboard/app.py`）都讀同一份。
- 開發**分階段**，每階段測試全綠才進下一段。
- 此環境需設 `OPENBLAS_NUM_THREADS=1`（已在 `src/__init__.py`、`conftest.py`、entry points、workflows 處理），否則 numpy/pandas 可能崩潰。

## 進度（全部完成）
階段 0 設定 ✅｜1 Alpaca 連線 ✅｜2 資料層 ✅｜3 策略引擎 ✅｜4 投組/再平衡 ✅｜
5 執行/通知 ✅｜6 報告 model/儲存 ✅｜7 Email ✅｜8 Dashboard ✅｜9 GitHub Actions ✅｜10 文件 ✅
（77 個測試全綠：`python -m pytest -q`）

## 架構與資料流
```
策略JSON ─► StrategyEngine(engine.py) ─► 目標權重(TargetPortfolio)
                       │ 透過 DataAdapter(adapter.py) 取 universe/動能
                       ▼
   weights_to_target_shares(sizing.py, 10%等權/整數股) ─► 目標股數
                       ▼
   should_rebalance(rebalance.py, 月初/新資金) ─► diff_orders ─► 買賣單
                       ▼
   execute_orders(trader.py, Paper) + notifier(即時通知)
                       ▼
   build_account_report(orchestrator.py) ─► 報告JSON(model.py) ─► store.py 存檔
                       ├─► email_view.py + email_sender.py（Gmail）
                       └─► dashboard/app.py（Streamlit，NAV/回撤可勾選 NASDAQ/SP500）
```

## 關鍵檔案
| 功能 | 檔案 |
|------|------|
| 帳戶設定 | `config/accounts.yaml` + `src/config/accounts.py` |
| 關注三大類別 | `config/watchlist.yaml` + `src/config/watchlist.py` |
| 策略定義 / schema | `strategies/*.json` + `strategies/schema.json` |
| 策略引擎 / 積木 | `src/strategy/engine.py`、`src/strategy/rules.py` |
| 配置與再平衡 | `src/portfolio/sizing.py`、`rebalance.py`、`state_store.py` |
| Alpaca 連線 | `src/brokers/alpaca_client.py` |
| 資料源 | `src/data/{market_data,fundamentals,universe,benchmarks,adapter}.py` |
| 報告 | `src/report/{model,metrics,store,email_view,email_sender}.py` |
| 串接流程 | `src/orchestrator.py` |
| 執行入口 | `scripts/run_trading.py`、`scripts/run_report.py`、`scripts/smoke_alpaca.py` |
| 自動化 | repo 根目錄 `.github/workflows/{trade,report}.yml` |

## 策略 JSON 規格（新增策略只加 JSON）
欄位：`name`、`universe{source,rank_by,top_n}`、`signals[{type,lookback_days}]`、
`selection{rank_by,order,top_n}`、`sizing{method,weight_per_position,shares}`、
`rebalance{schedule,on_new_cash}`、`constraints{long_only,max_positions}`。
目前支援的積木：universe source=`nasdaq`、signal=`momentum`、sizing=`equal_weight`、
rebalance schedule=`monthly_first_trading_day|daily|none`。範例見 `strategies/nasdaq_momentum_top10.json`。

## 怎麼做常見操作
- **新增策略**：複製 `strategies/nasdaq_momentum_top10.json` 改參數，存成新檔；無需改 Python。
- **新增帳戶**：在 `accounts.yaml` 加一筆（含 `key_env`/`secret_env`），並設定對應環境變數 / GitHub Secrets。每帳戶同時只綁一個策略，換策略改 `strategy` 欄位即可。
- **換成真實盤**：把該帳戶 `env: paper` 改 `live`（請先在 Paper 充分驗證）。

## 執行方式
```bash
cd alpaca_system
python -m pip install -r requirements.txt
# 設定環境變數（PowerShell）
$env:ALPACA_MAIN_KEY="..."; $env:ALPACA_MAIN_SECRET="..."
$env:OPENBLAS_NUM_THREADS="1"

python -m pytest -q                       # 跑全部測試
python scripts/smoke_alpaca.py            # 實連煙霧測試（讀帳戶/持倉/報價）
python scripts/run_trading.py --dry-run   # 交易（只規劃不送單）
python scripts/run_trading.py             # 交易（Paper 實際送單）
python scripts/run_report.py --no-email   # 產報告（不寄信）
streamlit run src/dashboard/app.py        # 開儀表板
```

## GitHub Actions
- `trade.yml`：cron `30 14 * * 1-5`（UTC，美股開盤後）走過所有帳戶執行買賣；可手動 + dry-run。
- `report.yml`：cron `0 22 * * 1-5`（UTC = 台灣 6:00）產報告 + 寄 Email + 把報告 JSON commit 回 repo。
- **需設定的 Secrets**：`ALPACA_MAIN_KEY`、`ALPACA_MAIN_SECRET`、`GMAIL_USER`、`GMAIL_APP_PASSWORD`、`REPORT_EMAIL_TO`。
- 注意：GitHub cron 是 UTC，不處理美國日光節約時間，觸發時刻會 ±1 小時。

## 雲端部署儀表板（不依賴本機、隨時可用）
儀表板**只讀報告 JSON、不連 Alpaca、不需要金鑰**，而報告由 `report.yml` 每天 commit 回 repo，
因此可部署到 **Streamlit Community Cloud**（免費），任何裝置有網路就能開：
1. 把整個 repo 推上 GitHub。
2. 到 share.streamlit.io 連結此 repo，設定：Branch=`master`、**Main file=`streamlit_app.py`**（repo 根）。
3. 依賴自動從 repo 根 `requirements.txt`（只含 streamlit/pandas/PyYAML/pydantic）安裝。
4. 之後每天 `report.yml` 更新 `alpaca_system/reports/*.json`，雲端儀表板讀到的就是最新資料。

相關設計：
- 帳戶清單由 `reports/` 資料夾掃出（`store.list_accounts`），**不依賴 `accounts.yaml`**，缺檔也能跑。
- 報告根目錄可用環境變數 `REPORTS_DIR` 覆寫（`store.default_root()`），預設讀 repo 內 `alpaca_system/reports/`。
- repo 根的 `streamlit_app.py` 是雲端入口；`.streamlit/config.toml` 為共用設定。
- 本機要開也可以：`streamlit run src/dashboard/app.py`。

## 資料限制與風險（白話）
- 「預測隔日十檔」無法真正準確 → 系統做的是**因子排名清單**，報告中明確標示為研究參考，非預測、非投資建議。
- yfinance（市值/本益比/大盤對比）為非官方來源，可能延遲或抓不到，僅供參考；抓不到時會優雅降級。
- Alpaca 免費行情為 IEX；Paper 成交是模擬撮合，與真實盤可能有落差。
- 10% 等權 + 整數股 → 會有現金零頭，屬正常。
- 自動下單若程式有誤可能造成實際虧損 → 這也是先用 Paper 的原因。
