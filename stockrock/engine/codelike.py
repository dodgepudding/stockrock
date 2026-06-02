"""Stock code prefix helpers (通达信 CODELIKE)."""


def normalize_code(code: str) -> str:
    return str(code).strip().split(".")[0].zfill(6)[:6]


def codelike(code: str, prefix: str) -> bool:
    return normalize_code(code).startswith(prefix)


def board_flags(code: str) -> dict[str, bool]:
    """
    SH: 深市主板(00) / 沪市主板(60)
    SZ: 创业板(30) / 科创板(68)
    SS: 北交所(4/8)
    FW: SH OR 30 (公式原文)
    """
    c = normalize_code(code)
    sh = codelike(c, "00") or codelike(c, "60")
    sz = codelike(c, "30") or codelike(c, "68")
    ss = codelike(c, "4") or codelike(c, "8")
    fw = sh or codelike(c, "30")
    return {"SH": sh, "SZ": sz, "SS": ss, "FW": fw}


def limit_up_ratio(code: str) -> float:
    """X1 in 勾魂选股."""
    b = board_flags(code)
    if b["SH"]:
        return 0.1
    if b["SZ"]:
        return 0.2
    if b["SS"]:
        return 0.3
    return 100.0
