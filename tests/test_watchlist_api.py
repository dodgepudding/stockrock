from unittest.mock import patch

from fastapi.testclient import TestClient

from stockrock.api.main import app
from stockrock.watchlist.store import WatchlistStore


def test_watchlist_list_without_quotes(tmp_path):
    store = WatchlistStore(path=tmp_path / "wl.json")
    store.add("600519", "茅台")

    with patch("stockrock.api.watchlist_routes._store", store):
        client = TestClient(app)
        r = client.get("/api/watchlist")
        assert r.status_code == 200
        assert r.json()["count"] == 1
        assert r.json()["items"][0]["code"] == "600519"


def test_watchlist_quotes_keeps_items_on_fetch_fail(tmp_path):
    store = WatchlistStore(path=tmp_path / "wl2.json")
    store.add("000001", "平安")

    with patch("stockrock.api.watchlist_routes._store", store):
        with patch(
            "stockrock.api.watchlist_routes.fetch_quotes",
            side_effect=RuntimeError("network down"),
        ):
            client = TestClient(app)
            r = client.get("/api/watchlist/quotes")
            assert r.status_code == 200
            data = r.json()
            assert data["count"] == 1
            assert data["items"][0]["code"] == "000001"
            assert data["quotes_ok"] is False
            assert data["items"][0].get("quote_error")


def test_watchlist_auto_fill_name_on_add(tmp_path):
    store = WatchlistStore(path=tmp_path / "wl4.json")

    with patch("stockrock.api.watchlist_routes._store", store):
        with patch(
            "stockrock.api.watchlist_routes.fetch_stock_names",
            return_value={"600519": "贵州茅台"},
        ):
            with patch(
                "stockrock.api.watchlist_routes._prices_for_codes",
                return_value={"600519": 100.0},
            ):
                client = TestClient(app)
                r = client.post("/api/watchlist", json={"code": "600519"})
                assert r.status_code == 200
                assert r.json()["item"]["name"] == "贵州茅台"


def test_watchlist_quotes_persists_missing_name(tmp_path):
    store = WatchlistStore(path=tmp_path / "wl5.json")
    store.add("600519", "")

    with patch("stockrock.api.watchlist_routes._store", store):
        with patch(
            "stockrock.api.watchlist_routes.fetch_quotes",
            return_value=[{"code": "600519", "price": 100.0, "name": "贵州茅台"}],
        ):
            with patch(
                "stockrock.api.watchlist_routes.fetch_stock_names",
                return_value={},
            ):
                client = TestClient(app)
                r = client.get("/api/watchlist/quotes")
                assert r.status_code == 200
                assert r.json()["items"][0]["name"] == "贵州茅台"
                assert store.list_items()[0]["name"] == "贵州茅台"


def test_watchlist_buy_sell_and_clear(tmp_path):
    store = WatchlistStore(path=tmp_path / "wl3.json")
    store.add("600519", "茅台")

    with patch("stockrock.api.watchlist_routes._store", store):
        with patch(
            "stockrock.api.watchlist_routes._prices_for_codes",
            return_value={"600519": 100.0},
        ):
            client = TestClient(app)
            rb = client.post("/api/watchlist/600519/buy", json={})
            assert rb.status_code == 200
            rb2 = client.post("/api/watchlist/600519/buy", json={"lots": 2, "price": 110})
            assert rb2.status_code == 200
            rs = client.post("/api/watchlist/600519/sell", json={"lots": 2, "price": 120})
            assert rs.status_code == 200
            rc = client.post("/api/watchlist/600519/sell", json={"all_close": True, "price": 130})
            assert rc.status_code == 200

        with patch(
            "stockrock.api.watchlist_routes.fetch_quotes",
            return_value=[{"code": "600519", "price": 130.0}],
        ):
            rq = client.get("/api/watchlist/quotes")
            assert rq.status_code == 200
            row = rq.json()["items"][0]
            assert row["position_lots"] == 0
            assert row["buy_count"] == 2
            assert row["sell_count"] == 2
            assert row["realized_pnl_pct"] is not None
