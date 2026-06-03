import os
import threading
import time
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd

from stockrock.watchlist.session import is_a_share_trading_session

_spot_cache: pd.DataFrame | None = None
_spot_cache_at: datetime | None = None
_spot_lock = threading.Lock()
CACHE_TTL_SECONDS = 45
FETCH_TIMEOUT_SECONDS = 8
CLOSE_LOOKBACK_DAYS = 30
SECTOR_CACHE_TTL_SECONDS = 3600
SECTOR_CANDIDATE_COLUMNS = ("所属行业", "行业", "板块", "概念")
_sector_cache: dict[str, str] | None = None
_sector_cache_at: datetime | None = None
_sector_lock = threading.Lock()
_symbol_name_cache: dict[str, str] | None = None
_symbol_name_cache_at: datetime | None = None
_symbol_name_lock = threading.Lock()
SYMBOL_NAME_CACHE_TTL_SECONDS = 86400


def _normalize_code(code: str) -> str:
    return str(code).strip().split(".")[0].zfill(6)[:6]


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


def _run_with_timeout(fn, timeout_seconds: int):
    result = {"value": None, "error": None}

    def worker():
        try:
            result["value"] = fn()
        except Exception as e:
            result["error"] = e

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout_seconds)
    if t.is_alive():
        raise TimeoutError(f"quote fetch timeout after {timeout_seconds}s")
    if result["error"] is not None:
        raise result["error"]
    return result["value"]


def _without_proxy(fn):
    keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "SOCKS_PROXY",
        "SOCKS5_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "socks_proxy",
        "socks5_proxy",
    ]
    saved = {k: os.environ.get(k) for k in keys if k in os.environ}
    try:
        for k in keys:
            os.environ.pop(k, None)
        return fn()
    finally:
        for k in keys:
            os.environ.pop(k, None)
        os.environ.update(saved)


def _load_spot_table() -> pd.DataFrame:
    global _spot_cache, _spot_cache_at
    with _spot_lock:
        now = datetime.now()
        if (
            _spot_cache is not None
            and _spot_cache_at is not None
            and (now - _spot_cache_at).total_seconds() < CACHE_TTL_SECONDS
        ):
            return _spot_cache

        def fetch():
            try:
                return _without_proxy(lambda: ak.stock_zh_a_spot())
            except Exception:
                return _without_proxy(lambda: ak.stock_zh_a_spot_em())

        try:
            raw = _run_with_timeout(lambda: _retry(fetch), FETCH_TIMEOUT_SECONDS)
        except Exception:
            if _spot_cache is not None:
                return _spot_cache
            raise
        raw["代码"] = raw["代码"].astype(str).str.zfill(6)
        _spot_cache = raw
        _spot_cache_at = now
        return raw


def _pick_sector(row: pd.Series) -> str | None:
    for col in SECTOR_CANDIDATE_COLUMNS:
        if col not in row.index:
            continue
        val = row[col]
        if pd.isna(val):
            continue
        s = str(val).strip()
        if s:
            return s
    return None


def fetch_major_sectors(codes: list[str]) -> dict[str, str]:
    if not codes:
        return {}
    code_set = {_normalize_code(c) for c in codes}
    out: dict[str, str] = {}

    # 优先：实时行情表中的行业字段（如果存在）
    try:
        spot = _load_spot_table()
        df = spot[spot["代码"].isin(code_set)]
        for _, row in df.iterrows():
            code = _normalize_code(row["代码"])
            sector = _pick_sector(row)
            if sector:
                out[code] = sector
    except Exception:
        pass

    # 回退：行业板块成分表（单独缓存），避免旧数据/新录入都缺失
    missing = [c for c in code_set if c not in out]
    if not missing:
        return out
    board_map = _load_sector_map_cache()
    for c in missing:
        s = board_map.get(c)
        if s:
            out[c] = s
    return out


def _load_symbol_name_map() -> dict[str, str]:
    global _symbol_name_cache, _symbol_name_cache_at
    with _symbol_name_lock:
        now = datetime.now()
        if (
            _symbol_name_cache is not None
            and _symbol_name_cache_at is not None
            and (now - _symbol_name_cache_at).total_seconds() < SYMBOL_NAME_CACHE_TTL_SECONDS
        ):
            return _symbol_name_cache
        try:
            from stockrock.data.cached_provider import CachedDataProvider

            df = CachedDataProvider().list_symbols()
            mapping = {
                _normalize_code(str(row["code"])): str(row["name"]).strip()
                for _, row in df.iterrows()
                if str(row.get("name") or "").strip()
            }
        except Exception:
            mapping = _symbol_name_cache or {}
        _symbol_name_cache = mapping
        _symbol_name_cache_at = now
        return mapping


def fetch_stock_names(codes: list[str]) -> dict[str, str]:
    """Resolve stock names: spot table first, then full A-share symbol list."""
    if not codes:
        return {}
    code_set = {_normalize_code(c) for c in codes}
    out: dict[str, str] = {}

    try:
        spot = _load_spot_table()
        df = spot[spot["代码"].isin(code_set)]
        for _, row in df.iterrows():
            code = _normalize_code(row["代码"])
            val = row.get("名称")
            if val is None or pd.isna(val):
                continue
            name = str(val).strip()
            if name:
                out[code] = name
    except Exception:
        pass

    missing = [c for c in code_set if c not in out]
    if missing:
        name_map = _load_symbol_name_map()
        for c in missing:
            name = name_map.get(c)
            if name:
                out[c] = name
    return out


def _load_sector_map_cache() -> dict[str, str]:
    global _sector_cache, _sector_cache_at
    with _sector_lock:
        now = datetime.now()
        if (
            _sector_cache is not None
            and _sector_cache_at is not None
            and (now - _sector_cache_at).total_seconds() < SECTOR_CACHE_TTL_SECONDS
        ):
            return _sector_cache
        try:
            mapping = _build_sector_map()
        except Exception:
            mapping = _sector_cache or {}
        _sector_cache = mapping
        _sector_cache_at = now
        return mapping


def _build_sector_map() -> dict[str, str]:
    names = _without_proxy(lambda: ak.stock_board_industry_name_em())
    if names is None or names.empty:
        return {}
    out: dict[str, str] = {}
    for _, row in names.iterrows():
        board = str(row.get("板块名称") or "").strip()
        if not board:
            continue
        try:
            cons = _without_proxy(lambda b=board: ak.stock_board_industry_cons_em(symbol=b))
        except Exception:
            continue
        if cons is None or cons.empty:
            continue
        for _, r in cons.iterrows():
            raw_code = str(r.get("代码") or r.get("证券代码") or "").strip()
            if not raw_code:
                continue
            code = _normalize_code(raw_code)
            if not code:
                continue
            if code not in out:
                out[code] = board
    return out


def _parse_spot_row(row: pd.Series) -> dict:
    col_map = {
        "代码": "code",
        "名称": "name",
        "最新价": "price",
        "涨跌幅": "change_pct",
        "涨跌额": "change",
        "今开": "open",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
    }
    item: dict = {"code": _normalize_code(row["代码"])}
    for cn, en in col_map.items():
        if cn not in row.index:
            continue
        val = row[cn]
        if pd.isna(val):
            item[en] = None
        elif en in ("price", "change", "change_pct", "open", "high", "low", "volume", "amount"):
            item[en] = float(val)
        else:
            item[en] = str(val)
    item["price_type"] = "realtime"
    sector = _pick_sector(row)
    if sector:
        item["major_sector"] = sector
    return item


def _fetch_spot_map(codes: list[str]) -> dict[str, dict]:
    spot = _load_spot_table()
    code_set = {_normalize_code(c) for c in codes}
    df = spot[spot["代码"].isin(code_set)]
    out: dict[str, dict] = {}
    for _, row in df.iterrows():
        item = _parse_spot_row(row)
        if item.get("price") is not None:
            out[item["code"]] = item
    return out


def _fetch_last_close(code: str) -> dict | None:
    """Latest daily bar close (for non-trading hours or spot fallback)."""
    from stockrock.data.cached_provider import CachedDataProvider

    code = _normalize_code(code)
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=CLOSE_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    try:
        df = CachedDataProvider().get_daily_bars(symbol=code, start=start, end=end)
    except Exception:
        return None
    if df is None or len(df) < 1:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else None
    close = float(last["close"])
    prev_close = float(prev["close"]) if prev is not None else close
    change = close - prev_close
    change_pct = (change / prev_close * 100.0) if prev_close else 0.0

    as_of = last["date"]
    if hasattr(as_of, "strftime"):
        as_of_s = as_of.strftime("%Y-%m-%d")
    else:
        as_of_s = str(as_of)[:10]

    return {
        "code": code,
        "price": close,
        "change": change,
        "change_pct": change_pct,
        "open": float(last["open"]),
        "high": float(last["high"]),
        "low": float(last["low"]),
        "volume": float(last["volume"]),
        "amount": float(last.get("amount") or 0),
        "price_type": "close",
        "as_of": as_of_s,
    }


def calc_initial_change_pct(
    initial_price: float | None, current_price: float | None
) -> float | None:
    if initial_price is None or current_price is None:
        return None
    if initial_price == 0:
        return None
    return (float(current_price) - float(initial_price)) / float(initial_price) * 100.0


def fetch_quotes(codes: list[str]) -> list[dict]:
    if not codes:
        return []

    code_list = sorted({_normalize_code(c) for c in codes})
    trading = is_a_share_trading_session()
    sector_map = fetch_major_sectors(code_list)
    name_map = fetch_stock_names(code_list)

    spot_map: dict[str, dict] = {}
    if trading:
        try:
            spot_map = _fetch_spot_map(code_list)
        except Exception:
            spot_map = {}

    out: list[dict] = []
    for code in code_list:
        if trading and code in spot_map:
            if code in sector_map and "major_sector" not in spot_map[code]:
                spot_map[code]["major_sector"] = sector_map[code]
            if code in name_map and not spot_map[code].get("name"):
                spot_map[code]["name"] = name_map[code]
            out.append(spot_map[code])
            continue
        close_q = _fetch_last_close(code)
        if close_q:
            if code in sector_map:
                close_q["major_sector"] = sector_map[code]
            if code in name_map:
                close_q["name"] = name_map[code]
            out.append(close_q)
        else:
            out.append(
                {
                    "code": code,
                    "quote_error": "暂无行情（可稍后刷新或先运行选股以缓存日线）",
                }
            )
    return out
