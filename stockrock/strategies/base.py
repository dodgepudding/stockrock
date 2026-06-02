from abc import ABC, abstractmethod
from typing import ClassVar

import pandas as pd


class Strategy(ABC):
    id: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str] = ""
    tdx_formula: ClassVar[str] = ""
    min_bars: ClassVar[int] = 30
    needs_capital: ClassVar[bool] = False

    @abstractmethod
    def signal(
        self,
        df: pd.DataFrame,
        code: str | None = None,
        name: str | None = None,
        capital_hands: float | None = None,
    ) -> pd.Series:
        """Return boolean Series aligned with df; True = condition met."""

    def latest_signal(
        self,
        df: pd.DataFrame,
        lookback_days: int = 1,
        code: str | None = None,
        name: str | None = None,
        capital_hands: float | None = None,
    ) -> bool:
        sig = self.signal(df, code=code, name=name, capital_hands=capital_hands)
        if sig is None or sig.empty:
            return False
        tail = sig.iloc[-lookback_days:]
        return bool(tail.any())

    def apply_params(self, params: dict | None) -> None:
        """Apply runtime parameters from API / Web (override on instance)."""
        if not params:
            return
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tdx_formula": self.tdx_formula,
            "params": self.get_param_schema(),
        }

    def get_param_schema(self) -> list[dict]:
        """Optional UI-editable parameters. Override in subclasses."""
        return []


_REGISTRY: dict[str, type[Strategy]] = {}


def register(cls: type[Strategy]) -> type[Strategy]:
    _REGISTRY[cls.id] = cls
    return cls


def list_strategies() -> list[dict]:
    return [cls().to_dict() for cls in _REGISTRY.values()]


def get_strategy(
    strategy_id: str, params: dict | None = None
) -> Strategy:
    if strategy_id not in _REGISTRY:
        raise KeyError(f"Unknown strategy: {strategy_id}")
    strategy = _REGISTRY[strategy_id]()
    strategy.apply_params(params)
    return strategy


def _load_builtin_strategies() -> None:
    import stockrock.strategies.example_ma_cross  # noqa: F401
    import stockrock.strategies.limit_up_relay  # noqa: F401
    import stockrock.strategies.uptrend_chips  # noqa: F401
    import stockrock.strategies.low_sideways_build  # noqa: F401
    import stockrock.strategies.soul_hook  # noqa: F401
    import stockrock.strategies.mizhuang_qinniu  # noqa: F401
    import stockrock.strategies.four_line_rise  # noqa: F401
    import stockrock.strategies.mizhuang_rebound  # noqa: F401
    import stockrock.strategies.qianfu_niugu  # noqa: F401
    import stockrock.strategies.zhuangjia_taijiao  # noqa: F401


_load_builtin_strategies()
