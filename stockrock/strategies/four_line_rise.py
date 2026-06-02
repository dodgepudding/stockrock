"""
四线主升 — 通达信指标

Original 通达信 formula (选股信号 GF_ZS23 / GF_ZS25):
  均线 5/10/30 + 空头排列 BARSLAST 时序 + MA30 金叉 + 回踩 MA30 突破

Translated: 2026-05-25
"""

import pandas as pd

from stockrock.indicators.tdx import BARSLAST, CROSS, MA, SUM_VAR
from stockrock.strategies.base import Strategy, register

_NEVER = 9999


def _barslast_or_never(cond: pd.Series) -> pd.Series:
    bl = BARSLAST(cond)
    return bl.where(bl >= 0, _NEVER)


@register
class FourLineRiseStrategy(Strategy):
    id = "four_line_rise"
    name = "四线主升"
    description = (
        "空头排列时序成立后，MA30 金叉 5/10 线，且回踩 MA30 后收盘站上 MA30"
        "（对应 GF_ZS23 主升买点）"
    )
    tdx_formula = """GF_ZS23:=LOW<GF_ZS7 AND CLOSE>GF_ZS7 AND GF_ZS21 AND GF_ZS14 AND GF_ZS22;
GF_ZS25:=GF_ZS23;"""
    min_bars = 40

    def signal(
        self,
        df: pd.DataFrame,
        code: str | None = None,
        name: str | None = None,
        capital_hands: float | None = None,
    ) -> pd.Series:
        c = df["close"].astype(float)
        l = df["low"].astype(float)

        zs1, zs2, zs3, zs4 = 5, 10, 30, 20
        zs5 = MA(c, zs1)
        zs6 = MA(c, zs2)
        zs7 = MA(c, zs3)

        zs8 = zs5 < zs6
        zs9 = zs5 < zs7
        zs10 = zs6 < zs7

        zs11 = BARSLAST(zs8)
        zs12 = BARSLAST(zs9)
        zs13 = BARSLAST(zs10)

        zs14 = (zs11 > zs12) & (zs12 > zs13) & (zs13 == 1) & (zs11 <= zs4)

        zs15 = CROSS(zs7, zs5)
        zs16 = CROSS(zs7, zs5) | CROSS(zs7, zs6)

        zs17 = _barslast_or_never(zs14)
        zs18 = _barslast_or_never(zs15)

        sum_zs16 = SUM_VAR(zs16.astype(float), zs17)
        zs19 = CROSS(sum_zs16, 0.5) & (zs17 < _NEVER)

        zs20 = BARSLAST(zs19)
        zs21 = zs17 < zs18

        zs20_safe = zs20.where(zs20 >= 0, _NEVER)
        zs22 = zs20_safe > zs17

        zs23 = (l < zs7) & (c > zs7) & zs21 & zs14 & zs22

        return zs23.fillna(False)
