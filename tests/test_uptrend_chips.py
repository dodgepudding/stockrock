import numpy as np
import pandas as pd

from stockrock.indicators.cyq import WINNER
from stockrock.indicators.tdx import BARSCOUNT
from stockrock.strategies.uptrend_chips import UptrendChipsStrategy


def test_barscount():
    s = pd.Series([1, 2, 3])
    bc = BARSCOUNT(s)
    assert bc.iloc[0] == 1
    assert bc.iloc[2] == 3


def test_winner_monotonic_uptrend():
    n = 50
    close = pd.Series(np.linspace(10, 20, n))
    high = close + 0.5
    low = close - 0.5
    vol = pd.Series([1000.0] * n)
    w = WINNER(close, high, low, vol)
    assert w.iloc[-1] > 0.9


def test_uptrend_chips_needs_200_bars():
    n = 100
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "open": [10.0] * n,
            "high": [11.0] * n,
            "low": [9.0] * n,
            "close": np.linspace(10, 20, n),
            "volume": [1_000_000.0] * n,
            "amount": [0.0] * n,
        }
    )
    sig = UptrendChipsStrategy().signal(df)
    assert not sig.iloc[-1]


def test_uptrend_chips_strong_uptrend():
    n = 250
    close = np.linspace(10, 50, n)
    df = pd.DataFrame(
        {
            "date": pd.date_range("2023-01-01", periods=n, freq="B"),
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": [1_000_000.0] * n,
            "amount": [0.0] * n,
        }
    )
    sig = UptrendChipsStrategy().signal(df)
    assert sig.iloc[-1]
