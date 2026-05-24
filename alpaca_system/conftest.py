"""讓 pytest 能以 `from src...` 匯入專案模組。"""
import os
import sys
from pathlib import Path

# 在匯入 numpy/pandas 之前限制 OpenBLAS 執行緒數，
# 避免此環境出現 "OpenBLAS Memory allocation failed" 而導致 Python 崩潰。
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
