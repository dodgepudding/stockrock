"""
低位横盘建仓 — 通达信选股条件（优化版）

Original 通达信 formula:
  庄家成本:=SUM(CLOSE*VOL,成本周期)/SUM(VOL,成本周期);
  量比:=VOL/MA(VOL,5);
  换手率:=VOL/CAPITAL*100;
  低位震荡:=ABS(CLOSE/MA(CLOSE,20)-1)<0.05;
  买入信号:=CLOSE<庄家成本*0.95 AND 量比>1.5 AND 换手率>2 AND 低位震荡;
  买入信号;

Translated: 2026-05-25
成本周期默认 60（可在策略类上改 cost_period）
CAPITAL 使用 AKShare 流通股，单位与通达信一致为「手」
"""

import pandas as pd

from stockrock.indicators.tdx import ABS, MA, SUM
from stockrock.strategies.base import Strategy, register


@register
class LowSidewaysBuildStrategy(Strategy):
    id = "low_sideways_build"
    name = "低位横盘建仓"
    description = (
        "收盘价低于量价成本5%以上；量比>1.5；换手率>2%；"
        "股价围绕20日均线±5%横盘（成本周期可在页面调整）"
    )
    tdx_formula = """庄家成本:=SUM(CLOSE*VOL,成本周期)/SUM(VOL,成本周期);
量比:=VOL/MA(VOL,5);
换手率:=VOL/CAPITAL*100;
低位震荡:=ABS(CLOSE/MA(CLOSE,20)-1)<0.05;
买入信号:=CLOSE<庄家成本*0.95 AND 量比>1.5 AND 换手率>2 AND 低位震荡;
买入信号;"""
    cost_period: int = 60
    min_bars: int = 60
    needs_capital: bool = True

    def get_param_schema(self) -> list[dict]:
        return [
            {
                "key": "cost_period",
                "label": "成本周期（日）",
                "type": "integer",
                "default": 60,
                "min": 5,
                "max": 250,
            }
        ]

    def apply_params(self, params: dict | None) -> None:
        if not params:
            return
        if "cost_period" in params and params["cost_period"] is not None:
            p = int(params["cost_period"])
            if p < 5 or p > 250:
                raise ValueError("cost_period 须在 5～250 之间")
            self.cost_period = p
            self.min_bars = max(p, 20)

    def signal(
        self,
        df: pd.DataFrame,
        code: str | None = None,
        name: str | None = None,
        capital_hands: float | None = None,
    ) -> pd.Series:
        c = df["close"]
        vol = df["volume"]
        n = self.cost_period

        vol_sum = SUM(vol, n)
        dealer_cost = SUM(c * vol, n) / vol_sum.replace(0, float("nan"))

        vol_ratio = vol / MA(vol, 5)
        if capital_hands is None or capital_hands <= 0:
            turnover = pd.Series(False, index=df.index)
        else:
            turnover = vol / capital_hands * 100

        sideways = ABS(c / MA(c, 20) - 1) < 0.05

        buy = (c < dealer_cost * 0.95) & (vol_ratio > 1.5) & (turnover > 2) & sideways
        return buy.fillna(False)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["needs_capital"] = True
        return d
