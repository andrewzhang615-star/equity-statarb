"""Tests for the Phase 2 abnormal-volume computation."""
import numpy as np
import pandas as pd

from src.signals.volume import abnormal_volume


def test_constant_volume_gives_av_of_one():
    dates = pd.date_range("2020-01-01", periods=80, freq="B")
    dv = pd.DataFrame({"a": [1e6] * 80}, index=dates)
    av = abnormal_volume(dv, window=5, base_window=60, min_base=30)
    assert abs(av["a"].iloc[-1] - 1.0) < 1e-9


def test_recent_volume_spike_raises_av():
    dates = pd.date_range("2020-01-01", periods=80, freq="B")
    vol = [1e6] * 75 + [2e6] * 5           # last 5 days double the base
    dv = pd.DataFrame({"a": vol}, index=dates)
    av = abnormal_volume(dv, window=5, base_window=60, min_base=30)
    assert abs(av["a"].iloc[-1] - 2.0) < 1e-6


def test_no_overlap_between_window_and_base():
    # A spike INSIDE the 5d window must not contaminate the base (which is shifted
    # by the window length): base uses data ending 5 days before t.
    dates = pd.date_range("2020-01-01", periods=80, freq="B")
    vol = [1e6] * 75 + [10e6] * 5
    dv = pd.DataFrame({"a": vol}, index=dates)
    av = abnormal_volume(dv, window=5, base_window=60, min_base=30)
    assert abs(av["a"].iloc[-1] - 10.0) < 1e-6  # base stays 1e6 -> AV = 10
