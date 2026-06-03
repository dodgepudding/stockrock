from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from stockrock.watchlist.quotes import (
    _normalize_code,
    calc_initial_change_pct,
    fetch_quotes,
    fetch_stock_names,
)
from stockrock.watchlist.store import WatchlistStore

router = APIRouter(prefix="/api/watchlist")
_store = WatchlistStore()


class WatchlistAddRequest(BaseModel):
    code: str
    name: str = ""
    source_strategy: str = ""


class WatchlistBatchRequest(BaseModel):
    items: list[WatchlistAddRequest] = Field(default_factory=list)


class TradeRequest(BaseModel):
    price: float | None = None
    lots: int = 1
    trade_at: str | None = None
    all_close: bool = False


def _trade_summary(trades: list[dict], current_price: float | None = None) -> dict:
    buy_queue: list[dict] = []
    position_lots = 0
    realized_cost = 0.0
    realized_amount = 0.0
    buy_count = 0
    sell_count = 0
    last_buy = None
    last_sell = None

    for t in trades or []:
        side = t.get("side")
        lots = int(t.get("lots") or 0)
        price = float(t.get("price") or 0)
        if lots <= 0 or price <= 0:
            continue
        if side == "buy":
            buy_count += 1
            last_buy = t
            buy_queue.append({"lots": lots, "price": price})
            position_lots += lots
        elif side == "sell":
            sell_count += 1
            last_sell = t
            remaining = lots
            realized_amount += price * lots
            while remaining > 0 and buy_queue:
                head = buy_queue[0]
                use = min(remaining, head["lots"])
                realized_cost += use * head["price"]
                head["lots"] -= use
                remaining -= use
                position_lots -= use
                if head["lots"] == 0:
                    buy_queue.pop(0)

    open_cost = sum(x["lots"] * x["price"] for x in buy_queue)
    avg_buy_price = (open_cost / position_lots) if position_lots > 0 else None
    realized_pnl = realized_amount - realized_cost
    realized_pnl_pct = (realized_pnl / realized_cost * 100.0) if realized_cost > 0 else None

    floating_pnl_pct = None
    if current_price is not None and avg_buy_price and avg_buy_price > 0:
        floating_pnl_pct = (float(current_price) - avg_buy_price) / avg_buy_price * 100.0

    return {
        "position_lots": position_lots,
        "avg_buy_price": avg_buy_price,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "last_buy_at": last_buy.get("trade_at") if last_buy else None,
        "last_buy_price": last_buy.get("price") if last_buy else None,
        "last_sell_at": last_sell.get("trade_at") if last_sell else None,
        "last_sell_price": last_sell.get("price") if last_sell else None,
        "realized_pnl_pct": realized_pnl_pct,
        "floating_pnl_pct": floating_pnl_pct,
    }


def _persist_missing_names(items: list[dict], quotes_by_code: dict[str, dict]) -> None:
    names_to_save: dict[str, str] = {}
    for it in items:
        if (it.get("name") or "").strip():
            continue
        code = it["code"]
        qname = (quotes_by_code.get(code, {}).get("name") or "").strip()
        if qname:
            names_to_save[code] = qname
    still_missing = [
        it["code"] for it in items if not (it.get("name") or "").strip() and it["code"] not in names_to_save
    ]
    if still_missing:
        names_to_save.update(fetch_stock_names(still_missing))
    if names_to_save:
        _store.enrich_names(names_to_save)


def _merge_items_with_quotes(items: list[dict]) -> tuple[list[dict], str | None]:
    """Always return one row per watchlist item; quotes optional."""
    if not items:
        return [], None
    global_error = None
    quotes_by_code: dict[str, dict] = {}
    try:
        quotes = fetch_quotes([it["code"] for it in items])
        quotes_by_code = {q["code"]: q for q in quotes}
    except Exception as e:
        global_error = str(e)

    _persist_missing_names(items, quotes_by_code)

    merged = []
    for it in items:
        q = quotes_by_code.get(it["code"], {})
        row = {**it}
        if q:
            for k, v in q.items():
                if k != "code":
                    row[k] = v
        if row.get("error"):
            row["quote_error"] = row.pop("error")
        elif global_error and row.get("price") is None:
            row["quote_error"] = global_error
        elif row.get("price") is None and not row.get("quote_error"):
            row["quote_error"] = "暂无行情"
        row["initial_change_pct"] = calc_initial_change_pct(
            row.get("initial_price"), row.get("price")
        )
        row.update(_trade_summary(row.get("trades", []), row.get("price")))
        merged.append(row)
    return merged, global_error


def _prices_for_codes(codes: list[str]) -> dict[str, float | None]:
    if not codes:
        return {}
    try:
        quotes = fetch_quotes(codes)
    except Exception:
        return {}
    out: dict[str, float | None] = {}
    for q in quotes:
        code = q.get("code")
        if code:
            out[code] = q.get("price")
    return out


@router.get("")
def get_watchlist():
    items = _store.list_items()
    missing = [it["code"] for it in items if not (it.get("name") or "").strip()]
    if missing:
        names = fetch_stock_names(missing)
        if names:
            _store.enrich_names(names)
            items = _store.list_items()
    return {"items": items, "count": len(items)}


@router.post("")
def add_to_watchlist(req: WatchlistAddRequest):
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="code is required")
    code = _normalize_code(req.code)
    prices = _prices_for_codes([code])
    name = req.name.strip()
    if not name:
        name = fetch_stock_names([code]).get(code, "")
    item = _store.add(
        code,
        name,
        initial_price=prices.get(code),
        source_strategy=req.source_strategy,
    )
    return {"item": item, "ok": True}


@router.post("/batch")
def add_batch(req: WatchlistBatchRequest):
    if not req.items:
        raise HTTPException(status_code=400, detail="items is empty")
    codes = [i.code.strip() for i in req.items if i.code.strip()]
    prices = _prices_for_codes(codes)
    entries = []
    for i in req.items:
        if not i.code.strip():
            continue
        c = _normalize_code(i.code)
        name = i.name.strip()
        if not name:
            name = fetch_stock_names([c]).get(c, "")
        entries.append(
            {
                "code": i.code,
                "name": name,
                "initial_price": prices.get(c),
                "source_strategy": i.source_strategy,
            }
        )
    added = _store.add_batch(entries)
    return {"items": added, "count": len(added), "ok": True}


@router.delete("/{code}")
def remove_from_watchlist(code: str):
    if not _store.remove(code):
        raise HTTPException(status_code=404, detail="Not in watchlist")
    return {"ok": True, "code": code}


@router.get("/quotes")
def watchlist_quotes():
    items = _store.list_items()
    merged, global_error = _merge_items_with_quotes(items)
    return {
        "items": merged,
        "count": len(merged),
        "quotes_ok": global_error is None,
        "quote_error": global_error,
    }


@router.post("/{code}/buy")
def buy_watchlist(code: str, req: TradeRequest):
    norm = _normalize_code(code)
    price = req.price
    if price is None:
        price = _prices_for_codes([norm]).get(norm)
    if price is None:
        raise HTTPException(status_code=400, detail="price is required when quote unavailable")
    try:
        item = _store.record_trade(
            norm, "buy", float(price), lots=req.lots, trade_at=req.trade_at
        )
        return {"item": item, "ok": True}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{code}/sell")
def sell_watchlist(code: str, req: TradeRequest):
    norm = _normalize_code(code)
    price = req.price
    if price is None:
        price = _prices_for_codes([norm]).get(norm)
    if price is None:
        raise HTTPException(status_code=400, detail="price is required when quote unavailable")
    try:
        item = _store.record_trade(
            norm,
            "sell",
            float(price),
            lots=req.lots,
            trade_at=req.trade_at,
            all_close=req.all_close,
        )
        return {"item": item, "ok": True}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
