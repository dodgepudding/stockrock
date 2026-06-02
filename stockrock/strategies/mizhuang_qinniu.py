"""
觅庄擒牛 — 通达信指标

Original 通达信 formula:
  GF_MZ34:=(CLOSE-LLV(LOW,34))/(HHV(HIGH,34)-LLV(LOW,34))*100;
  K34:=SMA(GF_MZ34,3,1); D34:=SMA(K34,3,1); J34:=3*K34-2*D34;
  (89、275 周期同理)
  GF_HA1:=CROSS(K34,D34);
  AA2:=CROSS(K89,D89); AA3:=CROSS(K275,D275);
  GF_HA1F:=EMA(CLOSE,7)-EMA(CLOSE,19); GF_HA1A:=EMA(GF_HA1F,9);
  AA4:=CROSS(GF_HA1F,GF_HA1A);
  共振擒牛:=GF_HA1 AND EXIST(AA2,5) AND EXIST(AA3,5) AND AA4;

Translated: 2026-05-25
选股条件 = 共振擒牛（最新 K 线）
"""

import numpy as np
import pandas as pd

from stockrock.indicators.tdx import CROSS, EMA, EXIST, HHV, LLV, SMA
from stockrock.strategies.base import Strategy, register


def _gf_mz(
    close: pd.Series, high: pd.Series, low: pd.Series, period: int
) -> pd.Series:
    """(C-LLV(L,n))/(HHV(H,n)-LLV(L,n))*100"""
    ll = LLV(low, period)
    hh = HHV(high, period)
    denom = (hh - ll).replace(0, np.nan)
    return ((close - ll) / denom * 100).fillna(50.0)


def _kdj_triple(
    close: pd.Series, high: pd.Series, low: pd.Series, period: int
) -> tuple[pd.Series, pd.Series, pd.Series]:
    gf = _gf_mz(close, high, low, period)
    k = SMA(gf, 3, 1)
    d = SMA(k, 3, 1)
    j = 3 * k - 2 * d
    return k, d, j


@register
class MizhuangQinniuStrategy(Strategy):
    id = "mizhuang_qinniu"
    name = "觅庄擒牛"
    description = (
        "共振擒牛：34 周期 K 上穿 D；近 5 日内 89、275 周期也曾金叉；"
        "快慢 EMA 差值上穿其 9 日平滑"
    )
    tdx_formula = """GF_HA1:=CROSS(K34,D34);
AA2:=CROSS(K89,D89); AA3:=CROSS(K275,D275);
AA4:=CROSS(GF_HA1F,GF_HA1A);
共振擒牛:=GF_HA1 AND EXIST(AA2,5) AND EXIST(AA3,5) AND AA4;"""
    min_bars = 300

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

        k34, d34, _ = _kdj_triple(c, h, l, 34)
        k89, d89, _ = _kdj_triple(c, h, l, 89)
        k275, d275, _ = _kdj_triple(c, h, l, 275)

        gf_ha1 = CROSS(k34, d34)
        aa2 = CROSS(k89, d89)
        aa3 = CROSS(k275, d275)

        gf_ha1f = EMA(c, 7) - EMA(c, 19)
        gf_ha1a = EMA(gf_ha1f, 9)
        aa4 = CROSS(gf_ha1f, gf_ha1a)

        resonance = gf_ha1 & EXIST(aa2, 5) & EXIST(aa3, 5) & aa4
        return resonance.fillna(False)
