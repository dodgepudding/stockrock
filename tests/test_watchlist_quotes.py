from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from stockrock.watchlist.quotes import fetch_major_sectors, fetch_quotes
from stockrock.watchlist.session import CN_TZ, is_a_share_trading_session


def test_trading_session_weekday_morning():
    dt = datetime(2026, 5, 25, 10, 0, tzinfo=CN_TZ)  # Monday
    assert is_a_share_trading_session(dt) is True


def test_trading_session_weekend():
    dt = datetime(2026, 5, 24, 10, 0, tzinfo=CN_TZ)  # Sunday
    assert is_a_share_trading_session(dt) is False


def test_trading_session_after_close():
    dt = datetime(2026, 5, 25, 16, 0, tzinfo=CN_TZ)
    assert is_a_share_trading_session(dt) is False


@patch("stockrock.watchlist.quotes.is_a_share_trading_session", return_value=False)
@patch("stockrock.watchlist.quotes._fetch_last_close")
def test_fetch_quotes_close_outside_session(mock_close, _mock_session):
    mock_close.return_value = {
        "code": "600519",
        "price": 1688.0,
        "change": 1.0,
        "change_pct": 0.06,
        "open": 1680.0,
        "high": 1690.0,
        "low": 1675.0,
        "volume": 1000.0,
        "amount": 0.0,
        "price_type": "close",
        "as_of": "2026-05-23",
    }
    out = fetch_quotes(["600519"])
    assert len(out) == 1
    assert out[0]["price"] == 1688.0
    assert out[0]["price_type"] == "close"
    assert out[0]["as_of"] == "2026-05-23"
    mock_close.assert_called_once_with("600519")


@patch("stockrock.watchlist.quotes.is_a_share_trading_session", return_value=True)
@patch("stockrock.watchlist.quotes._fetch_spot_map")
def test_fetch_quotes_spot_during_session(mock_spot, _mock_session):
    mock_spot.return_value = {
        "600519": {
            "code": "600519",
            "price": 1690.0,
            "change_pct": 0.1,
            "price_type": "realtime",
        }
    }
    out = fetch_quotes(["600519"])
    assert out[0]["price"] == 1690.0
    assert out[0]["price_type"] == "realtime"


@patch("stockrock.watchlist.quotes.is_a_share_trading_session", return_value=True)
@patch("stockrock.watchlist.quotes._fetch_spot_map", return_value={})
@patch("stockrock.watchlist.quotes._fetch_last_close")
def test_fetch_quotes_fallback_close_when_spot_missing(mock_close, _spot, _session):
    mock_close.return_value = {
        "code": "000001",
        "price": 12.5,
        "change": 0.1,
        "change_pct": 0.8,
        "open": 12.4,
        "high": 12.6,
        "low": 12.3,
        "volume": 1.0,
        "amount": 0.0,
        "price_type": "close",
        "as_of": "2026-05-23",
    }
    out = fetch_quotes(["000001"])
    assert out[0]["price"] == 12.5
    assert out[0]["price_type"] == "close"


@patch("stockrock.watchlist.quotes._load_sector_map_cache", return_value={"600519": "酿酒行业"})
@patch("stockrock.watchlist.quotes._load_spot_table", side_effect=RuntimeError("spot down"))
def test_fetch_major_sectors_fallback_to_board_map(_spot, _board):
    out = fetch_major_sectors(["600519", "000001"])
    assert out["600519"] == "酿酒行业"
