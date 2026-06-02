"""
觅庄抢反弹 — 通达信指标

Original 通达信 formula:
  GF_MZ21:=(CLOSE-LLV(LOW,36))/(HHV(HIGH,36)-LLV(LOW,36))*100;
  GF_MZ22:=SMA(GF_MZ21,3,1);
  GF_MZ23:=SMA(GF_MZ22,3,1);
  GF_MZ24:=SMA(GF_MZ23,3,1);
  波:=GF_MZ23; 段:=GF_MZ24;
  GF_MZ26:=CROSS(GF_MZ23,GF_MZ24) AND GF_MZ23<20;

Translated: 2026-05-25
选股条件 = GF_MZ26
"""

import pandas as pd

from stockrock.indicators.tdx import CROSS, SMA
from stockrock.strategies.base import Strategy, register
from stockrock.strategies.mizhuang_qinniu import _gf_mz


@register
class MizhuangReboundStrategy(Strategy):
    id = "mizhuang_rebound"
    name = "觅庄抢反弹"
    description = "36 日 RSV 三连 SMA：波上穿段且波<20（低位抢反弹）"
    tdx_formula = """GF_MZ26:=CROSS(GF_MZ23,GF_MZ24) AND GF_MZ23<20;
波:=GF_MZ23; 段:=GF_MZ24;"""
    min_bars = 55

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

        gf21 = _gf_mz(c, h, l, 36)
        gf22 = SMA(gf21, 3, 1)
        gf23 = SMA(gf22, 3, 1)
        gf24 = SMA(gf23, 3, 1)

        gf26 = CROSS(gf23, gf24) & (gf23 < 20)
        return gf26.fillna(False)
