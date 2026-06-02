from datetime import datetime
from pathlib import Path

import pandas as pd

from stockrock.data.base import BAR_COLUMNS


def merge_bar_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Merge bar DataFrames, dedupe by date (keep last)."""
    parts = [f for f in frames if f is not None and not f.empty]
    if not parts:
        return pd.DataFrame(columns=BAR_COLUMNS)
    out = pd.concat(parts, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    out = (
        out[BAR_COLUMNS]
        .drop_duplicates(subset=["date"], keep="last")
        .sort_values("date")
        .reset_index(drop=True)
    )
    return out


class BarCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str) -> Path:
        code = symbol.replace(".", "").upper()
        return self.cache_dir / f"{code}.parquet"

    def exists(self, symbol: str) -> bool:
        return self._path(symbol).exists()

    def get_bounds(self, symbol: str) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
        path = self._path(symbol)
        if not path.exists():
            return None, None
        df = pd.read_parquet(path, columns=["date"])
        if df.empty:
            return None, None
        dates = pd.to_datetime(df["date"])
        return dates.min(), dates.max()

    def get(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame | None:
        path = self._path(symbol)
        if not path.exists():
            return None
        df = pd.read_parquet(path)
        if df.empty:
            return None
        df["date"] = pd.to_datetime(df["date"])
        if start:
            df = df[df["date"] >= pd.Timestamp(start)]
        if end:
            df = df[df["date"] <= pd.Timestamp(end)]
        return df.reset_index(drop=True) if not df.empty else None

    def put(self, symbol: str, df: pd.DataFrame) -> None:
        if df is None or df.empty:
            return
        out = df.copy()
        out["date"] = pd.to_datetime(out["date"])
        for col in BAR_COLUMNS:
            if col not in out.columns:
                if col == "amount":
                    out["amount"] = 0.0
                else:
                    raise ValueError(f"Missing column {col}")
        out = out[BAR_COLUMNS].sort_values("date")
        path = self._path(symbol)
        if path.exists():
            existing = pd.read_parquet(path)
            existing["date"] = pd.to_datetime(existing["date"])
            out = merge_bar_frames([existing, out])
        out.to_parquet(path, index=False)

    def is_fresh(self, symbol: str, max_age_hours: int = 24) -> bool:
        """File mtime within max_age_hours (optional fast-path hint)."""
        path = self._path(symbol)
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return (datetime.now() - mtime).total_seconds() < max_age_hours * 3600
