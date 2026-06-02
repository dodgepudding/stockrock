from datetime import datetime, timedelta

import pandas as pd
import pytest

from stockrock.data.base import BAR_COLUMNS
from stockrock.data.cache import BarCache, merge_bar_frames
from stockrock.data.cached_provider import CachedDataProvider


def _bars(code: str, dates: list[str], base: float = 10.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "open": [base] * len(dates),
            "high": [base + 1] * len(dates),
            "low": [base - 1] * len(dates),
            "close": [base] * len(dates),
            "volume": [1000.0] * len(dates),
            "amount": [0.0] * len(dates),
        }
    )


class MockProvider:
    def __init__(self, data: dict[str, pd.DataFrame]):
        self.data = data
        self.calls: list[tuple[str, str, str]] = []

    def list_symbols(self, market: str = "A") -> pd.DataFrame:
        return pd.DataFrame({"code": list(self.data.keys()), "name": ["x"] * len(self.data)})

    def get_daily_bars(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        self.calls.append((symbol, start or "", end or ""))
        df = self.data.get(symbol, pd.DataFrame(columns=BAR_COLUMNS)).copy()
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"])
        if start:
            df = df[df["date"] >= pd.Timestamp(start)]
        if end:
            df = df[df["date"] <= pd.Timestamp(end)]
        return df.reset_index(drop=True)


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache"


def test_merge_bar_frames_dedupe():
    a = _bars("1", ["2024-01-01", "2024-01-02"], 10)
    b = _bars("1", ["2024-01-02", "2024-01-03"], 20)
    m = merge_bar_frames([a, b])
    assert len(m) == 3
    assert m.loc[m["date"] == pd.Timestamp("2024-01-02"), "close"].iloc[0] == 20


def test_incremental_only_fetches_new_bars(cache_dir):
    old_dates = pd.bdate_range("2024-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    new_dates = pd.bdate_range("2024-01-15", periods=5).strftime("%Y-%m-%d").tolist()
    all_dates = sorted(set(old_dates + new_dates))

    full = _bars("600519", all_dates)
    initial = full[full["date"].isin(pd.to_datetime(old_dates))]
    incremental = full[full["date"].isin(pd.to_datetime(new_dates))]

    provider = MockProvider({"600519": full})
    cached = CachedDataProvider(
        provider=provider,
        cache_dir=cache_dir,
        max_cache_age_hours=0,
        incremental_overlap_days=3,
    )

    cached.get_daily_bars("600519", start=old_dates[0], end=old_dates[-1])
    assert len(provider.calls) == 1

    provider.calls.clear()
    cached.get_daily_bars("600519", start=old_dates[0], end=new_dates[-1])
    assert len(provider.calls) == 1
    inc_start, inc_end = provider.calls[0][1], provider.calls[0][2]
    assert pd.Timestamp(inc_start) >= pd.Timestamp(old_dates[-1]) - timedelta(days=10)
    assert pd.Timestamp(inc_end) == pd.Timestamp(new_dates[-1])

    result = cached.get_daily_bars("600519", start=old_dates[0], end=new_dates[-1])
    assert len(result) == len(all_dates)


def test_cache_hit_no_network_when_fresh(cache_dir):
    dates = pd.bdate_range("2024-06-01", periods=30).strftime("%Y-%m-%d").tolist()
    provider = MockProvider({"000001": _bars("000001", dates)})
    cached = CachedDataProvider(
        provider=provider, cache_dir=cache_dir, max_cache_age_hours=24
    )
    cached.get_daily_bars("000001", start=dates[0], end=dates[-1])
    provider.calls.clear()
    cached.get_daily_bars("000001", start=dates[0], end=dates[-1])
    assert len(provider.calls) == 0
