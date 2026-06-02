import numpy as np
import pandas as pd

from stockrock.strategies.mizhuang_qinniu import MizhuangQinniuStrategy, _gf_mz


def test_gf_mz_range():
    n = 50
    c = pd.Series(np.linspace(10, 15, n))
    h = c + 1
    l = c - 1
    gf = _gf_mz(c, h, l, 10)
    assert gf.min() >= 0
    assert gf.max() <= 100


def test_mizhuang_qinniu_runs():
    n = 320
    close = np.linspace(10, 20, n)
    df = pd.DataFrame(
        {
            "date": pd.date_range("2023-01-01", periods=n, freq="B"),
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": [1e6] * n,
            "amount": [0.0] * n,
        }
    )
    sig = MizhuangQinniuStrategy().signal(df)
    assert len(sig) == n
    assert sig.dtype == bool
