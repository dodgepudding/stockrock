"""
庄家抬轿 — 通达信指标

Original 通达信 formula:
  DIFF:=EMA(CLOSE,6) - EMA(CLOSE,13);
  DEA:=EMA(DIFF,5);
  RSV:=(CLOSE-LLV(LOW,9))/(HHV(HIGH,9)-LLV(LOW,9));
  K:=SMA(RSV,9,3); D:=SMA(K,9,3); J:=3*K-2*D;
  A:=CROSS(DIFF,DEA) AND CROSS(K,D) AND CROSS(J,D) AND DIFF<0;
  A7:=FILTER(A,20);

Translated: 2026-05-25
选股条件 = A7
"""

import numpy as np
import pandas as pd

from stockrock.indicators.tdx import CROSS, EMA, FILTER, HHV, LLV, SMA
from stockrock.strategies.base import Strategy, register


def _rsv_ratio(
    close: pd.Series, high: pd.Series, low: pd.Series, period: int
) -> pd.Series:
    ll = LLV(low, period)
    hh = HHV(high, period)
    denom = (hh - ll).replace(0, np.nan)
    return ((close - ll) / denom).fillna(0.5)


@register
class ZhuangjiaTaijiaoStrategy(Strategy):
    id = "zhuangjia_taijiao"
    name = "庄家抬轿"
    description = (
        "MACD 负区 DIFF 上穿 DEA，且 KDJ 的 K、J 同日上穿 D；"
        "20 日内 FILTER 去重"
    )
    tdx_formula = """A:=CROSS(DIFF,DEA) AND CROSS(K,D) AND CROSS(J,D) AND DIFF<0;
A7:=FILTER(A,20);"""
    min_bars = 45

    def signal(
        self,
        df: pd.DataFrame,
        code: str | None = None,
        name: str | None = None,
        capital_hands: float | None = None,
    ) -> pd.Series:
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)

        diff = EMA(c, 6) - EMA(c, 13)
        dea = EMA(diff, 5)

        rsv = _rsv_ratio(c, h, l, 9)
        k = SMA(rsv, 9, 3)
        d = SMA(k, 9, 3)
        j = 3 * k - 2 * d

        a = CROSS(diff, dea) & CROSS(k, d) & CROSS(j, d) & (diff < 0)
        return FILTER(a, 20).fillna(False)
