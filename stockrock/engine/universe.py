from dataclasses import dataclass

import pandas as pd

from stockrock.data.cached_provider import CachedDataProvider


@dataclass
class UniverseFilter:
    exclude_st: bool = True
    exclude_bj: bool = True
    include_kcb: bool = True
    include_cyb: bool = True
    min_list_days: int = 60
    max_symbols: int | None = None


def build_universe(
    provider: CachedDataProvider | None = None,
    filt: UniverseFilter | None = None,
) -> pd.DataFrame:
    filt = filt or UniverseFilter()
    provider = provider or CachedDataProvider()
    df = provider.list_symbols()

    if filt.exclude_st:
        df = df[~df["name"].str.contains("ST", case=False, na=False)]
        df = df[~df["name"].str.contains("退", na=False)]

    def board_ok(code: str) -> bool:
        if filt.exclude_bj and code.startswith(("4", "8")):
            return False
        if not filt.include_kcb and code.startswith("688"):
            return False
        if not filt.include_cyb and code.startswith("300"):
            return False
        return True

    df = df[df["code"].apply(board_ok)]

    if filt.max_symbols:
        df = df.head(filt.max_symbols)

    return df.reset_index(drop=True)
