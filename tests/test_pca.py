"""Tests for the Layer C rolling-PCA residualization."""
import numpy as np
import pandas as pd

from src.signals.pca import pca_residuals


def _panel(T=320, N=40, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2019-01-01", periods=T, freq="B")
    f = rng.normal(0, 0.02, T)                       # one strong common factor
    beta = rng.uniform(0.5, 1.5, N)
    noise = rng.normal(0, 0.002, (T, N))             # small idiosyncratic piece
    R = pd.DataFrame(np.outer(f, beta) + noise, index=dates, columns=range(N))
    E = pd.DataFrame(True, index=dates, columns=range(N))
    return R, E


def test_pca_removes_common_factor():
    R, E = _panel()
    resid, diag = pca_residuals(R, E, window=252, n_factors=3, reestimate=21)
    valid = resid.notna().any(axis=1)
    raw_var = R[valid].var().mean()
    res_var = resid[valid].var().mean()
    assert res_var < 0.15 * raw_var                  # common factor stripped out
    assert (diag["var_explained"] > 0.8).all()       # 1-factor world: top PCs dominate


def test_causality_future_returns_dont_change_past_residuals():
    R, E = _panel()
    resid1, _ = pca_residuals(R, E, window=252, n_factors=3, reestimate=21)
    R2 = R.copy()
    R2.iloc[-1] = R2.iloc[-1] + 0.5                  # perturb only the last day
    resid2, _ = pca_residuals(R2, E, window=252, n_factors=3, reestimate=21)
    pd.testing.assert_frame_equal(resid1.iloc[:-1], resid2.iloc[:-1])


def test_low_coverage_name_gets_nan():
    R, E = _panel()
    R.iloc[: int(252 * 0.6), 0] = np.nan             # name 0: <60% window coverage at t0=251
    resid, _ = pca_residuals(R, E, window=252, n_factors=3, reestimate=300)
    assert resid.iloc[251:270, 0].isna().all()       # excluded, not fabricated
    assert resid.iloc[251:270, 1].notna().all()      # others unaffected
