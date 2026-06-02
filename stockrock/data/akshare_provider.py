import time
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd

from stockrock.data.base import BAR_COLUMNS, DataProvider


def _retry(fn, retries: int = 3, delay: float = 1.0):
    last_err = None
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if i < retries - 1:
                time.sleep(delay * (i + 1))
    raise last_err


def _normalize_code(symbol: str) -> str:
    s = symbol.strip().upper()
    if "." in s:
        return s.split(".")[0]
    return s


class AKShareProvider(DataProvider):
    def list_symbols(self, market: str = "A") -> pd.DataFrame:
        def fetch():
            return ak.stock_info_a_code_name()

        raw = _retry(fetch)
        df = raw.rename(columns={"code": "code", "name": "name"})
        df["code"] = df["code"].astype(str).str.zfill(6)
        return df[["code", "name"]].reset_index(drop=True)

    def get_daily_bars(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        code = _normalize_code(symbol)

        if not end:
            end = datetime.now().strftime("%Y%m%d")
        if not start:
            start = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y%m%d")
        start_s = start.replace("-", "")[:8]
        end_s = end.replace("-", "")[:8]

        adjust_map = {"qfq": "qfq", "hfq": "hfq", "none": ""}
        adj = adjust_map.get(adjust, "qfq")

        def fetch():
            return ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_s,
                end_date=end_s,
                adjust=adj,
            )

        raw = _retry(fetch)
        if raw is None or raw.empty:
            return pd.DataFrame(columns=BAR_COLUMNS)

        col_map = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
        }
        df = raw.rename(columns=col_map)
        df["date"] = pd.to_datetime(df["date"])
        for c in ["open", "high", "low", "close", "volume", "amount"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        if "amount" not in df.columns:
            df["amount"] = 0.0
        return df[BAR_COLUMNS].sort_values("date").reset_index(drop=True)
