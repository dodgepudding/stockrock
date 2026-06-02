"""
Original 通达信 formula:
  MA5:=MA(C,5);
  MA10:=MA(C,10);
  CROSS(MA5, MA10);

Translated: 2026-05-25
"""

import pandas as pd

from stockrock.indicators.tdx import CROSS, MA
from stockrock.strategies.base import Strategy, register


@register
class MaCrossStrategy(Strategy):
    id = "ma_cross"
    name = "均线金叉"
    description = "5日均线上穿10日均线（通达信 CROSS 语义）"
    tdx_formula = """MA5:=MA(C,5);
MA10:=MA(C,10);
CROSS(MA5, MA10);"""

    def signal(
        self,
        df: pd.DataFrame,
        code: str | None = None,
        name: str | None = None,
        capital_hands: float | None = None,
    ) -> pd.Series:
        c = df["close"]
        ma5 = MA(c, 5)
        ma10 = MA(c, 10)
        return CROSS(ma5, ma10)
