"""Signal-construction tests: winsorization, reversal sign, eligibility masking.

Key invariant: winsorization caps the SIGNAL input only and never mutates the
caller's returns (which are the realized-PnL panel).
"""
import pandas as pd

from src.backtest import engine
from src.signals.reversal import reversal_signal, winsorize


def test_winsorize_caps_and_does_not_mutate():
    df = pd.DataFrame({"x": [5.0, -5.0, 0.01]})
    out = winsorize(df, -0.20, 0.20)
    assert out["x"].max() == 0.20 and out["x"].min() == -0.20
    assert df["x"].iloc[0] == 5.0  # input untouched


def test_reversal_sign_and_no_mutation():
    dates = pd.date_range("2020-01-01", periods=6, freq="D")
    rets = pd.DataFrame({"A": [0.02] * 6, "B": [-0.02] * 6, "C": [0.0] * 6}, index=dates)
    sig = reversal_signal(rets, lookback=3, skip=0, winsor=(-0.20, 0.20))
    assert sig["A"].iloc[-1] < 0   # recent winner -> short
    assert sig["B"].iloc[-1] > 0   # recent loser -> long
    assert rets["A"].iloc[0] == 0.02  # returns panel not mutated


def test_signal_to_weights_respects_eligible():
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    sig = pd.DataFrame({"A": [1.0] * 4, "B": [-1.0] * 4, "C": [2.0] * 4}, index=dates)
    elig = pd.DataFrame(True, index=dates, columns=sig.columns)
    elig["C"] = False
    w = engine.signal_to_weights(sig, eligible=elig, market_neutral=True)
    assert (w["C"] == 0).all()                                   # ineligible -> no weight
    assert abs(w.drop(columns="C").sum(axis=1)).max() < 1e-9     # dollar-neutral over eligible
