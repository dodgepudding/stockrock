from abc import ABC, abstractmethod
from typing import Literal

import pandas as pd

ProviderName = Literal["akshare", "tushare"]

BAR_COLUMNS = ["date", "open", "high", "low", "close", "volume", "amount"]


class DataProvider(ABC):
    @abstractmethod
    def list_symbols(self, market: str = "A") -> pd.DataFrame:
        """Return DataFrame with columns: code, name, and optional metadata."""

    @abstractmethod
    def get_daily_bars(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """Return OHLCV bars with standard BAR_COLUMNS."""


def get_provider(name: ProviderName | None = None) -> DataProvider:
    from stockrock import config

    provider_name = (name or config.DATA_PROVIDER).lower()
    if provider_name == "tushare":
        from stockrock.data.tushare_provider import TushareProvider

        return TushareProvider()
    from stockrock.data.akshare_provider import AKShareProvider

    return AKShareProvider()
