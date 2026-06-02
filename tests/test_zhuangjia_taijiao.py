import numpy as np
import pandas as pd

from stockrock.strategies.zhuangjia_taijiao import ZhuangjiaTaijiaoStrategy


def test_zhuangjia_taijiao_runs():
    n = 80
    close = np.linspace(10, 11, n)
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
    sig = ZhuangjiaTaijiaoStrategy().signal(df)
    assert len(sig) == n
    assert sig.dtype == bool
