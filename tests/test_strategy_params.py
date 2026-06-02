import pytest

from stockrock.strategies.base import get_strategy
from stockrock.strategies.params import normalize_strategy_params


def test_normalize_cost_period():
    p = normalize_strategy_params("low_sideways_build", {"cost_period": 30})
    assert p == {"cost_period": 30}


def test_normalize_invalid_cost_period():
    with pytest.raises(ValueError):
        normalize_strategy_params("low_sideways_build", {"cost_period": 3})


def test_get_strategy_applies_cost_period():
    s = get_strategy("low_sideways_build", params={"cost_period": 40})
    assert s.cost_period == 40
    assert s.min_bars == 40
