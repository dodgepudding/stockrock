from datetime import datetime, timedelta

import pandas as pd

from stockrock import config
from stockrock.data.base import BAR_COLUMNS, DataProvider


def _normalize_code(symbol: str) -> str:
    s = symbol.strip().upper()
    if "." in s:
        return s
    if s.startswith(("6", "5", "9")):
        return f"{s}.SH"
    return f"{s}.SZ"


class TushareProvider(DataProvider):
    def __init__(self, token: str | None = None):
        self.token = token or config.TUSHARE_TOKEN
        if not self.token:
            raise ValueError(
                "TUSHARE_TOKEN is required when using tushare provider. "
                "Set it in .env or pass token=..."
            )
        try:
            import tushare as ts
        except ImportError as e:
            raise ImportError(
                "Install tushare: pip install 'stockrock[tushare]'"
            ) from e
        self._pro = ts.pro_api(self.token)

    def list_symbols(self, market: str = "A") -> pd.DataFrame:
        raw = self._pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name",
        )
        df = raw.rename(columns={"symbol": "code", "name": "name"})
        df["code"] = df["code"].astype(str).str.zfill(6)
        return df[["code", "name"]].reset_index(drop=True)

    def get_daily_bars(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        ts_code = _normalize_code(symbol)
        if not end:
            end = datetime.now().strftime("%Y%m%d")
        if not start:
            start = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y%m%d")
        start_s = start.replace("-", "")[:8]
        end_s = end.replace("-", "")[:8]

        adj_map = {"qfq": "qfq", "hfq": "hfq", "none": None}
        adj = adj_map.get(adjust, "qfq")

        raw = self._pro.pro_bar(
            ts_code=ts_code,
            adj=adj,
            start_date=start_s,
            end_date=end_s,
            freq="D",
        )
        if raw is None or raw.empty:
            return pd.DataFrame(columns=BAR_COLUMNS)

        df = raw.rename(
            columns={
                "trade_date": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "vol": "volume",
                "amount": "amount",
            }
        )
        df["date"] = pd.to_datetime(df["date"])
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce") * 100
        for c in BAR_COLUMNS[1:]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df[BAR_COLUMNS].sort_values("date").reset_index(drop=True)
