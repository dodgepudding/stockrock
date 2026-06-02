"""
上升趋势筹码 — 通达信选股条件

Original 通达信 formula:
  100*WINNER(C)>=95
  AND DYNAINFO(4)>0
  AND BARSCOUNT(C)>200;

Translated: 2026-05-25
Note: WINNER 由 OHLCV 筹码分布近似（见 indicators/cyq.py）
DYNAINFO(4) 映射为昨收 REF(C,1)>0
"""

import pandas as pd

from stockrock.indicators.cyq import WINNER
from stockrock.indicators.tdx import BARSCOUNT, REF
from stockrock.strategies.base import Strategy, register


@register
class UptrendChipsStrategy(Strategy):
    id = "uptrend_chips"
    name = "上升趋势筹码"
    description = (
        "收盘价位上获利筹码≥95%；昨收有效；上市交易超过200根K线。"
        "（WINNER 为日线筹码近似，可与通达信略有差异）"
    )
    tdx_formula = """100*WINNER(C)>=95
AND DYNAINFO(4)>0
AND BARSCOUNT(C)>200;"""
    min_bars = 201

    def signal(
        self,
        df: pd.DataFrame,
        code: str | None = None,
        name: str | None = None,
        capital_hands: float | None = None,
    ) -> pd.Series:
        c = df["close"]
        h = df["high"]
        l = df["low"]
        vol = df["volume"]

        winner_pct = 100 * WINNER(c, h, l, vol, price=c)
        cond_winner = winner_pct >= 95

        # DYNAINFO(4) = 昨收
        cond_dynainfo = REF(c, 1) > 0

        cond_bars = BARSCOUNT(c) > 200

        return cond_winner & cond_dynainfo & cond_bars
