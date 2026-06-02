import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_PROVIDER = os.getenv("STOCKROCK_DATA_PROVIDER", "akshare").lower()
CACHE_DIR = Path(os.getenv("STOCKROCK_CACHE_DIR", PROJECT_ROOT / "data" / "cache"))
WATCHLIST_PATH = Path(
    os.getenv("STOCKROCK_WATCHLIST_PATH", PROJECT_ROOT / "data" / "watchlist.json")
)
LOOKBACK_DAYS = int(os.getenv("STOCKROCK_LOOKBACK_DAYS", "120"))
# Overlap days when incrementally updating cache (handles revisions / holidays)
CACHE_INCREMENTAL_OVERLAP_DAYS = int(
    os.getenv("STOCKROCK_CACHE_INCREMENTAL_OVERLAP_DAYS", "5")
)
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")
HOST = os.getenv("STOCKROCK_HOST", "0.0.0.0")
PORT = int(os.getenv("STOCKROCK_PORT", "8000"))


def _default_screen_workers() -> int:
    n = os.cpu_count() or 4
    return min(16, n * 2)


SCREEN_WORKERS = max(
    1, int(os.getenv("STOCKROCK_SCREEN_WORKERS", str(_default_screen_workers())))
)
