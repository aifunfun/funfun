"""套件初始化：在匯入 numpy/pandas/matplotlib 前限制 OpenBLAS 執行緒數，
避免某些 Windows 環境出現 OpenBLAS 記憶體配置失敗而導致程式崩潰。"""
import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
