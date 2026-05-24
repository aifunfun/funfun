"""Streamlit Community Cloud 入口。

把儀表板部署到雲端後，任何裝置只要有網路就能開，不依賴你的本機電腦。
資料來自 GitHub repo 內 alpaca_system/reports/ 的報告 JSON（由 report.yml workflow 每天更新）。

在 Streamlit Community Cloud 設定：
  Repository  = 你的 GitHub repo
  Branch      = master
  Main file   = streamlit_app.py
（依賴會從 repo 根目錄的 requirements.txt 安裝。）
"""
import os
import sys
from pathlib import Path

# 匯入 pandas/numpy 前先限制 OpenBLAS 執行緒，避免部分環境記憶體配置失敗
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

# 讓 `from src...` 能匯入專案模組
PROJECT_DIR = Path(__file__).resolve().parent / "alpaca_system"
sys.path.insert(0, str(PROJECT_DIR))

from src.dashboard.app import main  # noqa: E402

main()
