"""Tests for the square-root market-impact model."""
import numpy as np
import pandas as pd

from src.execution.impact import participation_stats, sqrt_impact_base


def test_sqrt_impact_base_value():
    dates = pd.date_range("2020-01-01", periods=1, freq="D")
    dw = pd.DataFrame({"a": [0.01], "b": [0.04]}, index=dates)
    vol = pd.DataFrame({"a": [0.02], "b": [0.02]}, index=dates)
    adv = pd.DataFrame({"a": [1e6], "b": [1e6]}, index=dates)
    base = sqrt_impact_base(dw, vol, adv)
    # a: 0.01*0.02*sqrt(0.01/1e6)=2e-8 ; b: 0.04*0.02*sqrt(0.04/1e6)=1.6e-7
    assert abs(base.iloc[0] - (2e-8 + 1.6e-7)) < 1e-12


def test_participation_scales_linearly_with_aum():
    dates = pd.date_range("2020-01-01", periods=1, freq="D")
    dw = pd.DataFrame({"a": [0.02]}, index=dates)
    adv = pd.DataFrame({"a": [1e6]}, index=dates)
    s1 = participation_stats(dw, adv, 1e6)
    s2 = participation_stats(dw, adv, 2e6)
    assert abs(s1["avg"] - 0.02) < 1e-9
    assert abs(s2["avg"] - 2 * s1["avg"]) < 1e-9
