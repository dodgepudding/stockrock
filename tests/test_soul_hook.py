import numpy as np
import pandas as pd

from stockrock.engine.codelike import board_flags, limit_up_ratio
from stockrock.strategies.soul_hook import SoulHookStrategy


def test_board_flags_main():
    assert board_flags("600519")["SH"]
    assert limit_up_ratio("600519") == 0.1


def test_board_flags_chinext():
    assert board_flags("300750")["SZ"]
    assert limit_up_ratio("300750") == 0.2


def test_soul_hook_runs():
    n = 80
    close = np.linspace(10, 12, n)
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "open": close - 0.1,
            "high": close + 0.3,
            "low": close - 0.3,
            "close": close,
            "volume": [1_000_000.0] * n,
            "amount": [0.0] * n,
        }
    )
    sig = SoulHookStrategy().signal(df, code="600519")
    assert len(sig) == n
    assert sig.dtype == bool


def test_soul_hook_no_code():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=5, freq="B"),
            "open": [1, 2, 3, 4, 5],
            "high": [1, 2, 3, 4, 5],
            "low": [1, 2, 3, 4, 5],
            "close": [1, 2, 3, 4, 5],
            "volume": [100] * 5,
            "amount": [0] * 5,
        }
    )
    assert not SoulHookStrategy().signal(df).any()
