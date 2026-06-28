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


def test_sector_residual_leave_one_out():
    from src.signals.residual import sector_residuals

    dates = pd.date_range("2020-01-01", periods=2, freq="D")
    cols = list(range(1, 9))  # 1..6 in sector 10 (6 names), 7..8 in sector 20 (2 names)
    ret = pd.DataFrame(0.0, index=dates, columns=cols)
    ret[6] = 0.6  # one winner in sector 10
    sector = pd.DataFrame({c: (10 if c <= 6 else 20) for c in cols}, index=dates)
    elig = pd.DataFrame(True, index=dates, columns=cols)

    resid = sector_residuals(ret, sector, elig, min_peers=5)
    # winner's LOO benchmark excludes itself (mean of 5 zeros) -> residual is its full move
    assert abs(resid.loc[dates[0], 6] - 0.6) < 1e-6
    # a flat peer: LOO mean = (0.6-0)/5 = 0.12 -> residual -0.12
    assert abs(resid.loc[dates[0], 1] - (-0.12)) < 1e-6
    # sector 20 has only 1 peer excl self (< min_peers) -> NaN, untradable
    assert pd.isna(resid.loc[dates[0], 7])


def test_sector_residual_accepts_nullable_eligible():
    # Regression: parquet-loaded/reindexed eligibility can be pandas nullable
    # boolean (object on .to_numpy()); sector_residuals must coerce to bool, not crash.
    from src.signals.residual import sector_residuals

    dates = pd.date_range("2020-01-01", periods=1, freq="D")
    cols = list(range(1, 8))  # 7 names, one sector (6 peers excl self >= min_peers)
    ret = pd.DataFrame(0.0, index=dates, columns=cols)
    ret[1] = 0.7
    sector = pd.DataFrame({c: 10 for c in cols}, index=dates)
    elig = pd.DataFrame(True, index=dates, columns=cols).astype("boolean")  # nullable dtype
    resid = sector_residuals(ret, sector, elig, min_peers=5)  # must not raise
    assert abs(resid.loc[dates[0], 1] - 0.7) < 1e-6


def test_ewma_smooth_identity_and_smoothing():
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    sig = pd.DataFrame({"a": [1.0, -1.0] * 5}, index=dates)  # alternating -> high churn
    assert engine.ewma_smooth(sig, None).equals(sig)         # no smoothing -> identity
    sm = engine.ewma_smooth(sig, halflife=3)
    assert sm["a"].diff().abs().mean() < sig["a"].diff().abs().mean()  # smoother


def test_apply_holding_period_holds_between_rebalances():
    import numpy as np

    dates = pd.date_range("2020-01-01", periods=6, freq="D")
    w = pd.DataFrame({"a": np.arange(6, dtype=float)}, index=dates)  # 0,1,2,3,4,5
    held = engine.apply_holding_period(w, k=3)
    # rebalance on rows 0 and 3; rows 1-2 hold 0, rows 4-5 hold 3
    assert list(held["a"]) == [0, 0, 0, 3, 3, 3]


def test_signal_to_weights_respects_eligible():
    dates = pd.date_range("2020-01-01", periods=4, freq="D")
    sig = pd.DataFrame({"A": [1.0] * 4, "B": [-1.0] * 4, "C": [2.0] * 4}, index=dates)
    elig = pd.DataFrame(True, index=dates, columns=sig.columns)
    elig["C"] = False
    w = engine.signal_to_weights(sig, eligible=elig, market_neutral=True)
    assert (w["C"] == 0).all()                                   # ineligible -> no weight
    assert abs(w.drop(columns="C").sum(axis=1)).max() < 1e-9     # dollar-neutral over eligible
