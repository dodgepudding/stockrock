import pandas as pd

from stockrock.indicators.tdx import FILTER
from stockrock.strategies.qianfu_niugu import QianfuNiuguStrategy


def test_filter_suppresses_repeat():
    cond = pd.Series([False, True, True, True, False, True])
    f = FILTER(cond, 2)
    assert f.iloc[1]
    assert not f.iloc[2]
    assert not f.iloc[3]
    assert f.iloc[5]


def test_qianfu_niugu_runs():
    import numpy as np

    n = 100
    close = np.linspace(10, 12, n)
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "open": close,
            "high": close + 0.3,
            "low": close - 0.3,
            "close": close,
            "volume": [1e6] * n,
            "amount": [0.0] * n,
        }
    )
    sig = QianfuNiuguStrategy().signal(df)
    assert len(sig) == n
    assert sig.dtype == bool
