"""
勾魂选股 — 通达信选股条件

Translated: 2026-05-25
Requires stock code for CODELIKE / board limit ratios (X1).
"""

import numpy as np
import pandas as pd

from stockrock.engine.codelike import board_flags, limit_up_ratio
from stockrock.indicators.tdx import (
    BARSLASTCOUNT,
    COUNT,
    DTPRICE,
    EVERY,
    IF,
    MAX_S,
    MIN_S,
    REF,
    ZTPRICE,
)
from stockrock.strategies.base import Strategy, register


def _codelike_series(index: pd.Index, flag: bool) -> pd.Series:
    return pd.Series(bool(flag), index=index)


@register
class SoulHookStrategy(Strategy):
    id = "soul_hook"
    name = "勾魂选股"
    description = (
        "涨停接力类形态过滤：昨日满足 T2，今日满足 TJDK；"
        "含板块涨跌幅、炸板/上影/量能等多条排除规则（需股票代码）"
    )
    tdx_formula = """XG:REF(T2,1) AND TJDK;
(含 SH/SZ/SS 板块、ZT/ZB/SB、T2 与 P1-P13 排除、TJ1-TJ3 过滤)"""
    min_bars = 70

    def signal(
        self,
        df: pd.DataFrame,
        code: str | None = None,
        name: str | None = None,
        capital_hands: float | None = None,
    ) -> pd.Series:
        if not code:
            return pd.Series(False, index=df.index)

        c = df["close"].astype(float)
        o = df["open"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        v = df["volume"].astype(float)
        ref_c1 = REF(c, 1)
        ref_h1 = REF(h, 1)

        bf = board_flags(code)
        SH = bf["SH"]
        SZ = bf["SZ"]
        SS = bf["SS"]
        FW = bf["FW"]
        x1 = limit_up_ratio(code)

        ztj = ZTPRICE(ref_c1, x1)
        zt = (np.isclose(c, h, rtol=0, atol=1e-4)) & (c >= ztj)
        dt = (np.isclose(c, l, rtol=0, atol=1e-4)) & (c <= DTPRICE(ref_c1, 0.1))
        zb = (c < h) & (h >= ztj)
        sb = zt & (COUNT(zt, 10) == 1)
        lbts = BARSLASTCOUNT(zt)

        syx = 100 * (h - MAX_S(c, o)) / ref_c1
        st = 100 * (c - o).abs() / ref_c1
        xyx = 100 * (MIN_S(c, o) - l) / ref_c1
        jzf = 100 * (o - ref_c1) / ref_c1
        zf = 100 * (c - ref_c1) / ref_c1
        vj = v < REF(v, 1)

        t1 = COUNT(zt, 2) > 0
        t2a = (syx > 5) & (c > o) & (xyx < 3) & (syx > st)

        t2b_ref = REF(
            zt & (jzf > 5) & (st > 3) & (l / ref_h1 > 1.03), 1
        )
        t2b_then = (~zb) & _codelike_series(c.index, SZ) & REF(zt, 2) & (
            l / ref_h1 < 1.03
        )
        t2b = IF(t2b_ref.fillna(False).astype(bool), t2b_then, True).astype(bool)

        t2c_ref = REF(zt & (COUNT(zt, 20) == 1) & (l / ref_h1 > 1.01), 2)
        t2c_bad = REF(
            ((jzf < 5) & (jzf > 0) & (zf < 0)) | ((xyx > 4) & (c > o)), 1
        ).fillna(False).astype(bool)
        t2c = IF(t2c_ref.fillna(False).astype(bool), ~t2c_bad, True).astype(bool)

        t2 = REF(t1, 1) & _codelike_series(c.index, FW) & t2a & t2b & t2c

        p1 = (
            (MAX_S(c, o) <= REF(MAX_S(c, o), 1))
            & (MIN_S(c, o) >= REF(MIN_S(c, o), 1))
            & REF(zt, 2)
            & REF((c < o) & (c > REF(c, 1)), 1)
        )
        p2 = (syx > 5) & (st > 5) & (jzf < -2) & REF(sb, 1)
        p3 = (
            REF(sb, 2)
            & EVERY((c > o) & (syx > 3) & (c > REF(c, 1)) & (h > REF(h, 1)) & (st < 2), 2)
        )
        p4 = (
            (st > 3)
            & (st < 4)
            & (h / ref_c1 > 1.09)
            & (xyx < 1.3)
            & REF(sb & (COUNT(zt, 20) == 1) & (jzf < 3), 1)
        )
        p5 = (
            (st > 3)
            & (st < 4)
            & (h / ref_c1 > 1.09)
            & (xyx < 1.3)
            & REF(zt & (st > 10) & _codelike_series(c.index, SZ), 1)
        )
        p6 = (syx > 2) & (xyx > 2) & (syx > xyx)
        p7 = (
            (MAX_S(c, o) <= REF(MAX_S(c, o), 1))
            & (MIN_S(c, o) >= REF(MIN_S(c, o), 1))
            & REF(zt, 2)
            & (v > REF(v, 1))
            & (COUNT(zt, 10) < 2)
        )
        p8 = EVERY(vj, 2) & REF(zt, 2)
        p9 = REF(sb, 1) & (jzf > 0) & (jzf < 2) & (st < 2) & (st > 1) & (~zb)
        p10 = (st > 4) & (jzf < -2) & REF(sb & (jzf > 2), 1)
        p11 = (COUNT(t2, 10) > 1) & REF(zt, 1)
        p12a = (
            (jzf < -4.1)
            & (o < REF(o, 1))
            & REF(zb & (c > o) & (o / ref_c1 > 1.01), 1)
        )
        p12 = p12a & REF(zt & (o / ref_c1 > 1.01), 2) & REF(c > o, 3)
        p13 = (
            REF((st > 10) & (COUNT(zt, 20) == 1), 2)
            & REF(syx > 9, 1)
            & _codelike_series(c.index, SH)
        )

        tj1 = IF(zb, jzf >= 0, ~zb).astype(bool) & (st > 0.4)
        tj2 = IF(np.isclose(xyx, 0, atol=1e-6), st > 6, xyx > 0).astype(bool)
        tj3 = (
            IF(zb, jzf > 9.5, ~zb).astype(bool)
            & (COUNT(EVERY(zb, 2), 5) == 0)
            & ~(zt & np.isclose(c, o, rtol=0, atol=1e-4))
        )

        ta = REF(
            tj1
            & tj2
            & (p1 == 0)
            & (p2 == 0)
            & (p3 == 0)
            & (p4 == 0)
            & (p5 == 0)
            & (p7 == 0)
            & (p8 == 0)
            & (p9 == 0)
            & (p10 == 0)
            & (p11 == 0),
            1,
        )
        tb = REF(tj3 & (p6 == 0), 2)
        tjp1 = (p12 == 0) & (p13 == 0)
        tjdk = (
            (jzf < 0)
            & (COUNT(lbts == 5, 60) < 2)
            & tjp1
            & ta
            & tb
        )

        xg = REF(t2, 1) & tjdk
        return xg.fillna(False)
