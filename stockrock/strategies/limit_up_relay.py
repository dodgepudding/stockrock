"""
涨停接力 — 通达信选股条件（X_4 按板块区分涨停幅度）

Original 通达信 formula:
  X_1:=REF(VOL,2)>1.5*MA(VOL,20) AND REF(VOL,2)<3*MA(VOL,20) AND REF(VOL,1)>1.5*REF(VOL,2) AND REF(VOL,1)<3*REF(VOL,2) AND VOL<0.9*REF(VOL,1);
  X_2:=REF(VOL,2)>1.5*REF(VOL,3) AND REF(VOL,2)<3*REF(VOL,3) AND REF(VOL,1)>1.5*REF(VOL,2) AND REF(VOL,1)<3*REF(VOL,2) AND VOL<0.9*REF(VOL,1);
  X_3:=X_1 OR X_2;
  X_4:=REF(CLOSE,2)-REF(CLOSE,3)>0.098*REF(CLOSE,3) AND REF(CLOSE,1)>REF(CLOSE,2) AND CLOSE>REF(LOW,1);
  X_5:=HIGH-IF(CLOSE>OPEN,CLOSE,OPEN)>0.15*(HIGH-LOW);
  X_3 AND X_4 AND EXIST(X_5,2);

Translated: 2026-05-25
Updated: X_4 涨停阈值 — 主板9.8% / 创业板&科创板19.8% / 北交所29.8% / ST4.8%
"""

import pandas as pd

from stockrock.engine.board import limit_up_ratio
from stockrock.indicators.tdx import EXIST, IF, MA, REF
from stockrock.strategies.base import Strategy, register


@register
class LimitUpRelayStrategy(Strategy):
    id = "limit_up_relay"
    name = "涨停接力"
    description = (
        "量能阶梯放大后当日缩量；两日前达板块涨停幅度、昨日收涨、今日收盘高于昨低；"
        "近2日存在较长上影线（主板10%/创科20%/北交30%/ST5%）"
    )
    tdx_formula = """X_1:=REF(VOL,2)>1.5*MA(VOL,20) AND REF(VOL,2)<3*MA(VOL,20) AND REF(VOL,1)>1.5*REF(VOL,2) AND REF(VOL,1)<3*REF(VOL,2) AND VOL<0.9*REF(VOL,1);
X_2:=REF(VOL,2)>1.5*REF(VOL,3) AND REF(VOL,2)<3*REF(VOL,3) AND REF(VOL,1)>1.5*REF(VOL,2) AND REF(VOL,1)<3*REF(VOL,2) AND VOL<0.9*REF(VOL,1);
X_3:=X_1 OR X_2;
X_4:=REF(CLOSE,2)-REF(CLOSE,3)>涨停比例*REF(CLOSE,3) AND REF(CLOSE,1)>REF(CLOSE,2) AND CLOSE>REF(LOW,1);
X_5:=HIGH-IF(CLOSE>OPEN,CLOSE,OPEN)>0.15*(HIGH-LOW);
X_3 AND X_4 AND EXIST(X_5,2);"""

    def signal(
        self,
        df: pd.DataFrame,
        code: str | None = None,
        name: str | None = None,
        capital_hands: float | None = None,
    ) -> pd.Series:
        vol = df["volume"]
        c = df["close"]
        o = df["open"]
        h = df["high"]
        l = df["low"]

        vol_2 = REF(vol, 2)
        vol_1 = REF(vol, 1)
        vol_3 = REF(vol, 3)
        ma_vol_20 = MA(vol, 20)

        x_1 = (
            (vol_2 > 1.5 * ma_vol_20)
            & (vol_2 < 3 * ma_vol_20)
            & (vol_1 > 1.5 * vol_2)
            & (vol_1 < 3 * vol_2)
            & (vol < 0.9 * vol_1)
        )

        x_2 = (
            (vol_2 > 1.5 * vol_3)
            & (vol_2 < 3 * vol_3)
            & (vol_1 > 1.5 * vol_2)
            & (vol_1 < 3 * vol_2)
            & (vol < 0.9 * vol_1)
        )

        x_3 = x_1 | x_2

        limit_ratio = limit_up_ratio(code or "", name=name)
        c_2 = REF(c, 2)
        c_3 = REF(c, 3)
        c_1 = REF(c, 1)
        x_4 = (
            (c_2 - c_3 > limit_ratio * c_3)
            & (c_1 > c_2)
            & (c > REF(l, 1))
        )

        body_top = IF(c > o, c, o)
        x_5 = (h - body_top) > 0.15 * (h - l)

        return x_3 & x_4 & EXIST(x_5, 2)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["board_thresholds"] = (
            "主板9.8% | 创业板/科创板19.8% | 北交所29.8% | ST4.8%"
        )
        return d
