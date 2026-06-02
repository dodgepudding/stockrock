import numpy as np
import pandas as pd

from stockrock.strategies.mizhuang_rebound import MizhuangReboundStrategy


def test_mizhuang_rebound_runs():
    n = 70
    close = np.linspace(12, 8, n)
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "open": close,
            "high": close + 0.4,
            "low": close - 0.4,
            "close": close,
            "volume": [1e6] * n,
            "amount": [0.0] * n,
        }
    )
    sig = MizhuangReboundStrategy().signal(df)
    assert len(sig) == n
    assert sig.dtype == bool
