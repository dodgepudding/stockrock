from datetime import datetime, timedelta

import pandas as pd

from stockrock import config
from stockrock.data.base import BAR_COLUMNS, DataProvider, get_provider
from stockrock.data.cache import BarCache, merge_bar_frames


def _to_ts(s: str | None) -> pd.Timestamp | None:
    if not s:
        return None
    return pd.Timestamp(s).normalize()


def _fmt_date(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%d")


class CachedDataProvider:
    """Wraps a DataProvider with Parquet bar cache and incremental updates."""

    def __init__(
        self,
        provider: DataProvider | None = None,
        cache_dir=None,
        max_cache_age_hours: int = 24,
        incremental_overlap_days: int | None = None,
    ):
        self.provider = provider or get_provider()
        self.cache = BarCache(cache_dir or config.CACHE_DIR)
        self.max_cache_age_hours = max_cache_age_hours
        self.incremental_overlap_days = (
            incremental_overlap_days
            if incremental_overlap_days is not None
            else config.CACHE_INCREMENTAL_OVERLAP_DAYS
        )

    def list_symbols(self, market: str = "A") -> pd.DataFrame:
        return self.provider.list_symbols(market=market)

    def _default_start(self) -> str:
        return (
            datetime.now() - timedelta(days=config.LOOKBACK_DAYS + 60)
        ).strftime("%Y-%m-%d")

    def _default_end(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _slice(
        self, df: pd.DataFrame, start: str | None, end: str | None
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=BAR_COLUMNS)
        out = df.copy()
        out["date"] = pd.to_datetime(out["date"])
        if start:
            out = out[out["date"] >= pd.Timestamp(start)]
        if end:
            out = out[out["date"] <= pd.Timestamp(end)]
        return out.reset_index(drop=True)

    def _fetch_and_merge(
        self,
        symbol: str,
        fetch_start: str,
        fetch_end: str,
        adjust: str,
        base_frames: list[pd.DataFrame],
    ) -> pd.DataFrame:
        fetched = self.provider.get_daily_bars(
            symbol=symbol,
            start=fetch_start,
            end=fetch_end,
            adjust=adjust,
        )
        merged = merge_bar_frames(base_frames + ([fetched] if fetched is not None else []))
        if not merged.empty:
            self.cache.put(symbol, merged)
        return merged

    def get_daily_bars(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        end_s = end or self._default_end()
        start_s = start or self._default_start()
        req_start = _to_ts(start_s)
        req_end = _to_ts(end_s)
        today = pd.Timestamp.now().normalize()
        if req_end is None or req_end > today:
            req_end = today
            end_s = _fmt_date(req_end)

        if force_refresh or not self.cache.exists(symbol):
            df = self._fetch_and_merge(symbol, start_s, end_s, adjust, [])
            return self._slice(df, start_s, end_s)

        cached = self.cache.get(symbol)
        if cached is None or cached.empty:
            df = self._fetch_and_merge(symbol, start_s, end_s, adjust, [])
            return self._slice(df, start_s, end_s)

        cache_min = pd.to_datetime(cached["date"].min()).normalize()
        cache_max = pd.to_datetime(cached["date"].max()).normalize()

        # Fast path: cache already covers request and file recently updated
        if (
            self.cache.is_fresh(symbol, self.max_cache_age_hours)
            and cache_min <= req_start
            and cache_max >= req_end
        ):
            return self._slice(cached, start_s, end_s)

        frames: list[pd.DataFrame] = [cached]
        overlap = timedelta(days=self.incremental_overlap_days)

        # Backfill older history if requested range starts before cache
        if req_start is not None and req_start < cache_min:
            back_end = cache_min - timedelta(days=1)
            if req_start <= back_end:
                back = self.provider.get_daily_bars(
                    symbol=symbol,
                    start=_fmt_date(req_start),
                    end=_fmt_date(back_end),
                    adjust=adjust,
                )
                if back is not None and not back.empty:
                    frames.insert(0, back)

        # Incremental forward: only download from (cache_max - overlap) to req_end
        if req_end > cache_max - timedelta(days=1):
            inc_start = max(
                cache_max - overlap,
                req_start if req_start is not None else cache_max - overlap,
            )
            if inc_start <= req_end:
                inc = self.provider.get_daily_bars(
                    symbol=symbol,
                    start=_fmt_date(inc_start),
                    end=end_s,
                    adjust=adjust,
                )
                if inc is not None and not inc.empty:
                    frames.append(inc)

        merged = merge_bar_frames(frames)
        if not merged.empty:
            self.cache.put(symbol, merged)
            from_cache = self.cache.get(symbol)
            if from_cache is not None and not from_cache.empty:
                merged = from_cache

        return self._slice(merged, start_s, end_s)
