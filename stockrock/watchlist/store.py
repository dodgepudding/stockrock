import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from stockrock import config


def _normalize_code(code: str) -> str:
    return str(code).strip().split(".")[0].zfill(6)[:6]


class WatchlistStore:
    def __init__(self, path: Path | None = None):
        self.path = path or config.WATCHLIST_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self._write({"items": []})

    def _read(self) -> dict:
        with self.path.open(encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def list_items(self) -> list[dict]:
        with self._lock:
            return list(self._read().get("items", []))

    def _holding_lots(self, item: dict) -> int:
        lots = 0
        for t in item.get("trades", []) or []:
            side = t.get("side")
            n = int(t.get("lots") or 0)
            if side == "buy":
                lots += n
            elif side == "sell":
                lots -= n
        return max(0, lots)

    def add(
        self,
        code: str,
        name: str = "",
        initial_price: float | None = None,
        source_strategy: str = "",
    ) -> dict:
        code = _normalize_code(code)
        with self._lock:
            data = self._read()
            items = data.get("items", [])
            for it in items:
                if it["code"] == code:
                    if name and not it.get("name"):
                        it["name"] = name
                    if source_strategy and not it.get("source_strategy"):
                        it["source_strategy"] = source_strategy
                    self._write(data)
                    return it
            item: dict = {
                "code": code,
                "name": name or "",
                "added_at": datetime.now(timezone.utc).isoformat(),
                "source_strategy": source_strategy or "",
                "trades": [],
            }
            if initial_price is not None:
                item["initial_price"] = round(float(initial_price), 4)
            items.append(item)
            data["items"] = items
            self._write(data)
            return item

    def add_batch(self, entries: list[dict]) -> list[dict]:
        added = []
        for e in entries:
            ip = e.get("initial_price")
            added.append(
                self.add(
                    e.get("code", ""),
                    e.get("name", ""),
                    initial_price=float(ip) if ip is not None else None,
                    source_strategy=e.get("source_strategy", ""),
                )
            )
        return added

    def enrich_names(self, names_by_code: dict[str, str]) -> int:
        """Fill empty item names from external lookup; returns update count."""
        if not names_by_code:
            return 0
        updated = 0
        with self._lock:
            data = self._read()
            items = data.get("items", [])
            for it in items:
                code = it["code"]
                new_name = (names_by_code.get(code) or "").strip()
                if new_name and not (it.get("name") or "").strip():
                    it["name"] = new_name
                    updated += 1
            if updated:
                self._write(data)
        return updated

    def remove(self, code: str) -> bool:
        code = _normalize_code(code)
        with self._lock:
            data = self._read()
            items = data.get("items", [])
            new_items = [it for it in items if it["code"] != code]
            if len(new_items) == len(items):
                return False
            data["items"] = new_items
            self._write(data)
            return True

    def record_trade(
        self,
        code: str,
        side: str,
        price: float,
        lots: int = 1,
        trade_at: str | None = None,
        all_close: bool = False,
    ) -> dict:
        code = _normalize_code(code)
        if side not in ("buy", "sell"):
            raise ValueError("side must be buy or sell")
        if lots <= 0:
            raise ValueError("lots must be > 0")
        if price <= 0:
            raise ValueError("price must be > 0")
        with self._lock:
            data = self._read()
            items = data.get("items", [])
            target = None
            for it in items:
                if it["code"] == code:
                    target = it
                    break
            if target is None:
                raise KeyError("Not in watchlist")

            target.setdefault("trades", [])
            current_lots = self._holding_lots(target)
            trade_lots = lots
            if side == "sell":
                if current_lots <= 0:
                    raise ValueError("no holding lots to sell")
                if all_close:
                    trade_lots = current_lots
                elif lots > current_lots:
                    raise ValueError("sell lots exceeds holding lots")

            target["trades"].append(
                {
                    "side": side,
                    "lots": int(trade_lots),
                    "price": float(price),
                    "trade_at": trade_at or datetime.now(timezone.utc).isoformat(),
                }
            )
            self._write(data)
            return target
