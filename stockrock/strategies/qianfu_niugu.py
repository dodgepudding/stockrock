"""
潜伏牛股 — 通达信指标

Original 通达信 formula:
  GF_Q1:=EMA(EMA(CLOSE,13),13);
  GF_Q2:=(GF_Q1-REF(GF_Q1,1))/REF(GF_Q1,1)*1000;
  GF_Q4:=(EMA(CLOSE,8)-EMA(CLOSE,55))*10;
  GF_Q5:=EMA(GF_Q4,3);
  GF_Q7:=GF_Q2>REF(GF_Q2,1) AND GF_Q2<-0.2;
  GF_Q8:=CROSS(GF_Q4,GF_Q5) AND GF_Q4<-0.3;
  潜伏牛股:=FILTER(GF_Q7 AND GF_Q8,13);

Translated: 2026-05-25
"""

import pandas as pd

from stockrock.indicators.tdx import CROSS, EMA, FILTER, REF
from stockrock.strategies.base import Strategy, register


@register
class QianfuNiuguStrategy(Strategy):
    id = "qianfu_niugu"
    name = "潜伏牛股"
    description = (
        "双EMA13 斜率回升但仍处低位；快慢EMA差金叉且处于负值区；"
        "13 日内不重复发信号（FILTER）"
    )
    tdx_formula = """GF_Q7:=GF_Q2>REF(GF_Q2,1) AND GF_Q2<-0.2;
GF_Q8:=CROSS(GF_Q4,GF_Q5) AND GF_Q4<-0.3;
潜伏牛股:=FILTER(GF_Q7 AND GF_Q8,13);"""
    min_bars = 70

    def signal(
        self,
        df: pd.DataFrame,
        code: str | None = None,
        name: str | None = None,
        capital_hands: float | None = None,
    ) -> pd.Series:
        c = df["close"].astype(float)

        gf_q1 = EMA(EMA(c, 13), 13)
        ref_q1 = REF(gf_q1, 1).replace(0, float("nan"))
        gf_q2 = (gf_q1 - ref_q1) / ref_q1 * 1000

        gf_q4 = (EMA(c, 8) - EMA(c, 55)) * 10
        gf_q5 = EMA(gf_q4, 3)

        gf_q7 = (gf_q2 > REF(gf_q2, 1)) & (gf_q2 < -0.2)
        gf_q8 = CROSS(gf_q4, gf_q5) & (gf_q4 < -0.3)

        raw = gf_q7 & gf_q8
        return FILTER(raw, 13).fillna(False)
