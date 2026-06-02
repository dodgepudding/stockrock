"""Validate strategy_params from API / Web."""


def normalize_strategy_params(
    strategy_id: str, params: dict | None
) -> dict | None:
    if not params:
        return None
    out: dict = {}
    if strategy_id == "low_sideways_build":
        if "cost_period" in params and params["cost_period"] is not None:
            p = int(params["cost_period"])
            if p < 5 or p > 250:
                raise ValueError("cost_period 须在 5～250 之间")
            out["cost_period"] = p
        return out or None
    return None
