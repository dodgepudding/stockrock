import numpy as np
import pandas as pd

from stockrock.strategies.low_sideways_build import LowSidewaysBuildStrategy


def _sample_df(n: int = 80) -> pd.DataFrame:
    close = np.full(n, 10.0)
    close[-1] = 8.0
    vol = np.full(n, 1_000_000.0)
    vol[-1] = 3_000_000.0
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "open": close,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
            "volume": vol,
            "amount": [0.0] * n,
        }
    )


def test_low_sideways_build_with_capital():
    df = _sample_df()
    capital = 1e8
    sig = LowSidewaysBuildStrategy().signal(df, capital_hands=capital)
    assert len(sig) == len(df)
    assert sig.dtype == bool


def test_low_sideways_no_capital_turnover_false():
    df = _sample_df()
    sig = LowSidewaysBuildStrategy().signal(df, capital_hands=None)
    assert not sig.iloc[-1]
