"""A-share trading session helpers (China local time)."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

CN_TZ = ZoneInfo("Asia/Shanghai")

# 沪深 A 股常规交易时段（不含集合竞价展示规则）
_MORNING = (time(9, 30), time(11, 30))
_AFTERNOON = (time(13, 0), time(15, 0))


def now_cn() -> datetime:
    return datetime.now(CN_TZ)


def is_a_share_trading_session(dt: datetime | None = None) -> bool:
    """True during weekday continuous auction sessions."""
    dt = dt or now_cn()
    if dt.weekday() >= 5:
        return False
    t = dt.time()
    return _MORNING[0] <= t <= _MORNING[1] or _AFTERNOON[0] <= t <= _AFTERNOON[1]
