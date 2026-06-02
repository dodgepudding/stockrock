from unittest.mock import patch

from fastapi.testclient import TestClient

from stockrock.api.main import app
from stockrock.watchlist.quotes import calc_initial_change_pct
from stockrock.watchlist.store import WatchlistStore


def test_calc_initial_change_pct():
    assert calc_initial_change_pct(100.0, 110.0) == 10.0
    assert calc_initial_change_pct(100.0, 90.0) == -10.0
    assert calc_initial_change_pct(None, 10.0) is None


def test_store_saves_initial_price(tmp_path):
    store = WatchlistStore(path=tmp_path / "wl.json")
    item = store.add(
        "600519", "茅台", initial_price=1688.5, source_strategy="均线金叉"
    )
    assert store.list_items()[0]["initial_price"] == 1688.5
    assert item["source_strategy"] == "均线金叉"
    again = store.add("600519", "茅台", initial_price=9999.0)
    assert again["initial_price"] == 1688.5


def test_watchlist_quotes_initial_change_pct(tmp_path):
    store = WatchlistStore(path=tmp_path / "wl2.json")
    store.add("600519", "茅台", initial_price=100.0)

    with patch("stockrock.api.watchlist_routes._store", store):
        with patch(
            "stockrock.api.watchlist_routes.fetch_quotes",
            return_value=[{"code": "600519", "price": 110.0}],
        ):
            client = TestClient(app)
            r = client.get("/api/watchlist/quotes")
            assert r.status_code == 200
            row = r.json()["items"][0]
            assert row["initial_price"] == 100.0
            assert row["initial_change_pct"] == 10.0


def test_add_watchlist_captures_initial_price(tmp_path):
    store = WatchlistStore(path=tmp_path / "wl3.json")

    with patch("stockrock.api.watchlist_routes._store", store):
        with patch(
            "stockrock.api.watchlist_routes._prices_for_codes",
            return_value={"600519": 50.25},
        ):
            client = TestClient(app)
            r = client.post(
                "/api/watchlist",
                json={
                    "code": "600519",
                    "name": "茅台",
                    "source_strategy": "均线金叉",
                },
            )
            assert r.status_code == 200
            assert r.json()["item"]["initial_price"] == 50.25
            assert r.json()["item"]["source_strategy"] == "均线金叉"
