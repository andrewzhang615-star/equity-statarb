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


def test_market_residual_removes_common_factor():
    import numpy as np
    from src.signals.residual import market_residuals

    dates = pd.date_range("2020-01-01", periods=80, freq="B")
    rng = np.random.default_rng(0)
    mkt = rng.normal(0, 0.01, len(dates))
    # every stock ~ 1.0 * market + tiny idiosyncratic noise
    df = pd.DataFrame({c: mkt + rng.normal(0, 1e-4, len(dates)) for c in "ABCD"}, index=dates)
    resid = market_residuals(df, window=40)
    tail = slice(60, None)  # after beta warmup
    # residual should retain only the (tiny) idio piece, far smaller than raw
    assert resid.iloc[tail].abs().mean().mean() < 0.2 * df.iloc[tail].abs().mean().mean()


def test_signal_to_weights_neutral_after_clip():
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    cols = [f"s{i}" for i in range(10)]
    sig = pd.DataFrame([[10.0] + [-1.0] * 9] * 3, index=dates, columns=cols)  # skewed -> clip binds
    w = engine.signal_to_weights(sig, max_weight=0.05, market_neutral=True)
    assert w.sum(axis=1).abs().max() < 1e-9  # dollar-neutral even after clipping


def test_signal_to_weights_respects_eligible():
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    sig = pd.DataFrame({"A": [1.0] * 4, "B": [-1.0] * 4, "C": [2.0] * 4}, index=dates)
    elig = pd.DataFrame(True, index=dates, columns=sig.columns)
    elig["C"] = False
    w = engine.signal_to_weights(sig, eligible=elig, market_neutral=True)
    assert (w["C"] == 0).all()                                   # ineligible -> no weight
    assert abs(w.drop(columns="C").sum(axis=1)).max() < 1e-9     # dollar-neutral over eligible
