import numpy as np
import pandas as pd

from stockrock.indicators.tdx import BARSLAST, SUM_VAR
from stockrock.strategies.four_line_rise import FourLineRiseStrategy


def test_barslast_never_true():
    cond = pd.Series([False, False, True, False])
    bl = BARSLAST(cond)
    assert bl.iloc[0] == -1
    assert bl.iloc[1] == -1
    assert bl.iloc[2] == 0
    assert bl.iloc[3] == 1


def test_sum_var():
    x = pd.Series([0, 1, 0, 1, 1], dtype=float)
    n = pd.Series([2, 2, 2, 3, 2])
    s = SUM_VAR(x, n)
    assert s.iloc[1] == 1
    assert s.iloc[3] == 2


def test_four_line_rise_runs():
    n = 80
    close = np.linspace(10, 15, n)
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
    sig = FourLineRiseStrategy().signal(df)
    assert len(sig) == n
    assert sig.dtype == bool
