"""
Tongdaxin-compatible indicator functions.

Conventions (match 通达信):
- REF(X, n): n bars ago (n=1 is previous bar)
- CROSS(A, B): today A>B and yesterday A<=B
- MA uses simple moving average over n bars including current
"""

import numpy as np
import pandas as pd


def _as_series(x) -> pd.Series:
    if isinstance(x, pd.Series):
        return x
    return pd.Series(x)


def REF(x, n: int = 1) -> pd.Series:
    s = _as_series(x)
    return s.shift(n)


def MA(x, n: int) -> pd.Series:
    s = _as_series(x)
    return s.rolling(window=n, min_periods=n).mean()


def EMA(x, n: int) -> pd.Series:
    s = _as_series(x)
    return s.ewm(span=n, adjust=False).mean()


def SMA(x, n: int, m: int = 1) -> pd.Series:
    """Tongdaxin SMA: Y = (M*X + (N-M)*Y')/N"""
    s = _as_series(x).astype(float)
    out = np.full(len(s), np.nan)
    if len(s) < n:
        return pd.Series(out, index=s.index)
    out[n - 1] = s.iloc[:n].mean()
    for i in range(n, len(s)):
        out[i] = (m * s.iloc[i] + (n - m) * out[i - 1]) / n
    return pd.Series(out, index=s.index)


def HHV(x, n: int) -> pd.Series:
    s = _as_series(x)
    return s.rolling(window=n, min_periods=1).max()


def LLV(x, n: int) -> pd.Series:
    s = _as_series(x)
    return s.rolling(window=n, min_periods=1).min()


def SUM(x, n: int) -> pd.Series:
    s = _as_series(x)
    return s.rolling(window=n, min_periods=1).sum()


def COUNT(cond, n: int) -> pd.Series:
    s = _as_series(cond).astype(bool)
    return s.rolling(window=n, min_periods=1).sum()


def FILTER(cond, n: int) -> pd.Series:
    """Suppress repeat signals for n bars after each trigger (通达信 FILTER)."""
    s = _as_series(cond).astype(bool)
    out = []
    suppress = 0
    for v in s:
        if suppress > 0:
            out.append(False)
            suppress -= 1
        elif v:
            out.append(True)
            suppress = n
        else:
            out.append(False)
    return pd.Series(out, index=s.index, dtype=bool)


def EXIST(cond, n: int) -> pd.Series:
    """True if cond was true at least once in the last n bars (incl. current)."""
    return COUNT(cond, n) > 0


def CROSS(a, b) -> pd.Series:
    a_s = _as_series(a)
    b_s = _as_series(b)
    if not isinstance(b, (pd.Series, np.ndarray, list)):
        b_s = float(b)
    prev_a = REF(a_s, 1)
    prev_b = REF(b_s, 1) if isinstance(b_s, pd.Series) else float(b)
    return (a_s > b_s) & (prev_a <= prev_b)


def LONGCROSS(a, b, n: int) -> pd.Series:
    a_s = _as_series(a)
    b_s = _as_series(b)
    below = a_s < b_s
    last_below = BARSLAST(below)
    return CROSS(a_s, b_s) & (last_below >= n)


def BARSLAST(cond) -> pd.Series:
    """Bars since cond was last true; -1 if never true before current bar."""
    s = _as_series(cond).astype(bool)
    out = []
    seen = False
    count = -1
    for v in s:
        if v:
            count = 0
            seen = True
        elif seen:
            count += 1
        else:
            count = -1
        out.append(float(count))
    return pd.Series(out, index=s.index, dtype=float)


def SUM_VAR(x, n: pd.Series) -> pd.Series:
    """SUM(X, N) when N is a per-bar series (通达信动态周期)."""
    xs = _as_series(x).astype(float)
    ns = _as_series(n).fillna(0).astype(int)
    out = []
    for i in range(len(xs)):
        period = int(ns.iloc[i])
        if period <= 0 or period >= 9999:
            out.append(0.0)
        else:
            start = max(0, i - period + 1)
            out.append(float(xs.iloc[start : i + 1].sum()))
    return pd.Series(out, index=xs.index)


def BARSSINCE(cond) -> pd.Series:
    s = _as_series(cond).astype(bool)
    out = []
    count = np.nan
    for v in s:
        if v:
            count = 0
        elif count is not np.nan and not pd.isna(count):
            count += 1
        out.append(count)
    return pd.Series(out, index=s.index)


def IF(cond, x, y) -> pd.Series:
    c = _as_series(cond).astype(bool)
    x_s = _as_series(x) if isinstance(x, (pd.Series, np.ndarray, list)) else x
    y_s = _as_series(y) if isinstance(y, (pd.Series, np.ndarray, list)) else y
    return pd.Series(np.where(c, x_s, y_s), index=c.index)


def AND(*conds) -> pd.Series:
    out = _as_series(conds[0]).astype(bool)
    for c in conds[1:]:
        out = out & _as_series(c).astype(bool)
    return out


def OR(*conds) -> pd.Series:
    out = _as_series(conds[0]).astype(bool)
    for c in conds[1:]:
        out = out | _as_series(c).astype(bool)
    return out


def ABS(x) -> pd.Series:
    return _as_series(x).abs()


def MAX_S(a, b) -> pd.Series:
    """Element-wise max of two series (通达信 MAX)."""
    return pd.Series(
        np.maximum(_as_series(a).astype(float), _as_series(b).astype(float)),
        index=_as_series(a).index,
    )


def MIN_S(a, b) -> pd.Series:
    """Element-wise min of two series (通达信 MIN)."""
    return pd.Series(
        np.minimum(_as_series(a).astype(float), _as_series(b).astype(float)),
        index=_as_series(a).index,
    )


def ZTPRICE(ref_close, ratio) -> pd.Series:
    """Limit-up price from prior close and ratio (e.g. 0.1 = 10%)."""
    s = _as_series(ref_close).astype(float)
    r = ratio if isinstance(ratio, (int, float)) else _as_series(ratio).astype(float)
    return (s * (1 + r)).round(2)


def DTPRICE(ref_close, ratio) -> pd.Series:
    """Limit-down price from prior close and ratio."""
    s = _as_series(ref_close).astype(float)
    r = ratio if isinstance(ratio, (int, float)) else _as_series(ratio).astype(float)
    return (s * (1 - r)).round(2)


def BARSLASTCOUNT(cond) -> pd.Series:
    """Consecutive bars with cond true ending at current bar."""
    s = _as_series(cond).astype(bool)
    out = []
    count = 0
    for v in s:
        if v:
            count += 1
        else:
            count = 0
        out.append(count)
    return pd.Series(out, index=s.index, dtype=float)


def EVERY(cond, n: int) -> pd.Series:
    """True when cond holds for every bar in the last n periods."""
    return COUNT(cond, n) >= n


def BARSCOUNT(x) -> pd.Series:
    """Bars since first data point in series (1-indexed, matches 通达信)."""
    s = _as_series(x)
    return pd.Series(np.arange(1, len(s) + 1), index=s.index, dtype=float)
