import pandas as pd

from stockrock.indicators.tdx import EXIST
from stockrock.strategies.limit_up_relay import LimitUpRelayStrategy


def test_exist_two_bars():
    cond = pd.Series([False, True, False])
    assert EXIST(cond, 2).iloc[1]
    assert EXIST(cond, 2).iloc[2]
    assert not EXIST(cond, 2).iloc[0]


def test_limit_up_relay_runs_on_sample():
    n = 40
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "open": [10.0] * n,
            "high": [10.5] * n,
            "low": [9.8] * n,
            "close": [10.0] * n,
            "volume": [1_000_000.0] * n,
            "amount": [0.0] * n,
        }
    )
    sig = LimitUpRelayStrategy().signal(df, code="600519")
    assert len(sig) == n
    assert sig.dtype == bool
