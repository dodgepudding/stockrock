"""
Chip distribution (CYQ) approximations for Tongdaxin functions.

WINNER is estimated from OHLCV: each bar's volume is spread uniformly
between low and high. This is close to Tongdaxin but not bit-identical
(通达信筹码衰减、换手系数未完全复刻).
"""

import numpy as np
import pandas as pd


def _winner_ratio_at(
    low: float,
    high: float,
    vol: float,
    price: float,
) -> tuple[float, float]:
    """Return (winner_volume, total_volume) for one bar."""
    if vol <= 0 or np.isnan(vol):
        return 0.0, 0.0
    if high <= low:
        w = vol if low < price else 0.0
        return w, vol
    if price >= high:
        return vol, vol
    if price <= low:
        return 0.0, vol
    frac = (price - low) / (high - low)
    return vol * frac, vol


def WINNER(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    volume: pd.Series,
    price: pd.Series | None = None,
    lookback: int | None = None,
) -> pd.Series:
    """
    Approximate Tongdaxin WINNER(price): fraction of chips with cost below price.

    Default price is close (WINNER(C)).
    lookback: max bars to include; None = all bars from listing in df.
    """
    c = np.asarray(close, dtype=float)
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    v = np.asarray(volume, dtype=float)
    p = np.asarray(price if price is not None else close, dtype=float)
    n = len(c)
    out = np.full(n, np.nan)

    for i in range(n):
        start = 0 if lookback is None else max(0, i - lookback + 1)
        winner_vol = 0.0
        total_vol = 0.0
        for j in range(start, i + 1):
            w, t = _winner_ratio_at(l[j], h[j], v[j], p[i])
            winner_vol += w
            total_vol += t
        out[i] = winner_vol / total_vol if total_vol > 0 else np.nan

    return pd.Series(out, index=close.index)
