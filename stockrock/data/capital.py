"""Circulating share capital (通达信 CAPITAL, unit: 手)."""

import re
import time
from functools import lru_cache

import akshare as ak


def _normalize_code(symbol: str) -> str:
    return str(symbol).strip().split(".")[0].zfill(6)[:6]


def _parse_share_value(raw: str) -> float | None:
    s = str(raw).strip().replace(",", "")
    if not s or s in ("-", "--", "nan"):
        return None
    mul = 1.0
    if "亿" in s:
        mul = 1e8
        s = s.replace("亿", "")
    elif "万" in s:
        mul = 1e4
        s = s.replace("万", "")
    m = re.search(r"[\d.]+", s)
    if not m:
        return None
    return float(m.group()) * mul


def _fetch_capital_shares(code: str) -> float | None:
    info = ak.stock_individual_info_em(symbol=code)
    if info is None or info.empty:
        return None
    item_col = "item" if "item" in info.columns else info.columns[0]
    val_col = "value" if "value" in info.columns else info.columns[1]

    for keyword in ("流通股", "流通股本", "流通A股"):
        rows = info[info[item_col].astype(str).str.contains(keyword, na=False)]
        if not rows.empty:
            shares = _parse_share_value(rows.iloc[0][val_col])
            if shares and shares > 0:
                return shares
    return None


@lru_cache(maxsize=8000)
def get_capital_hands(code: str) -> float | None:
    """
    Tongdaxin CAPITAL: circulating shares in 手 (1 手 = 100 股).
    AKShare hist 成交量 is also in 手, so turnover = VOL/CAPITAL*100.
    """
    code = _normalize_code(code)
    last_err = None
    for i in range(3):
        try:
            shares = _fetch_capital_shares(code)
            if shares is None:
                return None
            return shares / 100.0
        except Exception as e:
            last_err = e
            time.sleep(0.5 * (i + 1))
    return None
