import pytest

from stockrock.watchlist.store import WatchlistStore


@pytest.fixture
def store(tmp_path):
    return WatchlistStore(path=tmp_path / "watchlist.json")


def test_add_remove(store):
    store.add("600519", "贵州茅台")
    items = store.list_items()
    assert len(items) == 1
    assert items[0]["code"] == "600519"
    assert store.remove("600519")
    assert store.list_items() == []


def test_add_dedupe(store):
    store.add("000001", "平安")
    store.add("000001", "平安银行")
    assert len(store.list_items()) == 1


def test_batch(store):
    store.add_batch(
        [{"code": "600519", "name": "茅台"}, {"code": "000001", "name": "平安"}]
    )
    assert len(store.list_items()) == 2


def test_trade_validation(store):
    store.add("600519", "茅台")
    store.record_trade("600519", "buy", price=100, lots=2)
    with pytest.raises(ValueError):
        store.record_trade("600519", "sell", price=101, lots=3)
    item = store.record_trade("600519", "sell", price=101, all_close=True)
    assert item["trades"][-1]["lots"] == 2
