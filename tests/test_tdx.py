import numpy as np
import pandas as pd
import pytest

from stockrock.indicators.tdx import BARSLAST, COUNT, CROSS, MA, REF, SUM


def test_ref():
    s = pd.Series([1, 2, 3, 4, 5])
    assert REF(s, 1).iloc[2] == 2
    assert np.isnan(REF(s, 1).iloc[0])


def test_ma():
    s = pd.Series([1.0, 2, 3, 4, 5])
    m = MA(s, 3)
    assert m.iloc[2] == pytest.approx(2.0)
    assert m.iloc[4] == pytest.approx(4.0)


def test_cross():
    a = pd.Series([1, 2, 3, 2, 4])
    b = pd.Series([2, 2, 2, 3, 3])
    cross = CROSS(a, b)
    assert cross.iloc[2]
    assert not cross.iloc[0]


def test_count_sum():
    cond = pd.Series([True, False, True, True, False])
    assert COUNT(cond, 3).iloc[4] == 2
    s = pd.Series([1.0, 2, 3, 4, 5])
    assert SUM(s, 3).iloc[2] == 6


def test_barslast():
    cond = pd.Series([False, True, False, False, True])
    bl = BARSLAST(cond)
    assert bl.iloc[3] == 2
    assert bl.iloc[4] == 0
