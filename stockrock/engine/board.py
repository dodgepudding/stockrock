"""A-share board detection and limit-up gain thresholds."""

from enum import Enum


class Board(str, Enum):
    MAIN = "main"  # 沪深主板 10%
    CHINEXT = "chinext"  # 创业板 20%
    STAR = "star"  # 科创板 20%
    BSE = "bse"  # 北交所 30%
    ST = "st"  # ST/*ST 5%
    UNKNOWN = "unknown"


def normalize_code(code: str) -> str:
    return str(code).strip().split(".")[0].zfill(6)[:6]


def is_st_name(name: str | None) -> bool:
    if not name:
        return False
    n = name.upper()
    return "ST" in n or "*ST" in n


def detect_board(code: str, name: str | None = None) -> Board:
    if is_st_name(name):
        return Board.ST
    c = normalize_code(code)
    if c.startswith(("688", "689")):
        return Board.STAR
    if c.startswith(("300", "301")):
        return Board.CHINEXT
    if c.startswith(("8", "4")):
        return Board.BSE
    if c.startswith(("60", "00", "001", "002", "003")):
        return Board.MAIN
    return Board.UNKNOWN


# Slightly below exchange limit (aligns with Tongdaxin 0.098 style)
_LIMIT_UP_RATIO: dict[Board, float] = {
    Board.MAIN: 0.098,
    Board.CHINEXT: 0.198,
    Board.STAR: 0.198,
    Board.BSE: 0.298,
    Board.ST: 0.048,
    Board.UNKNOWN: 0.098,
}

_BOARD_LABEL: dict[Board, str] = {
    Board.MAIN: "主板10%",
    Board.CHINEXT: "创业板20%",
    Board.STAR: "科创板20%",
    Board.BSE: "北交所30%",
    Board.ST: "ST5%",
    Board.UNKNOWN: "默认10%",
}


def limit_up_ratio(code: str, name: str | None = None) -> float:
    """Min gain ratio (close-to-close) to treat as limit-up for X_4."""
    board = detect_board(code, name=name)
    return _LIMIT_UP_RATIO[board]


def board_label(code: str, name: str | None = None) -> str:
    return _BOARD_LABEL[detect_board(code, name=name)]
