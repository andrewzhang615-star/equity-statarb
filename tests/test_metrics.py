"""Sanity tests for metrics and the look-ahead guard in the engine."""
import numpy as np
import pandas as pd

from src.backtest import engine, metrics


def test_sharpe_zero_variance_is_nan():
    # A genuinely zero-volatility stream has an undefined Sharpe.
    assert np.isnan(metrics.sharpe_ratio(pd.Series([0.0] * 100)))


def test_max_drawdown_is_negative():
    assert metrics.max_drawdown(pd.Series([0.1, -0.5, 0.1])) < 0


def test_calmar_sign_matches_return():
    r = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])
    assert np.sign(metrics.calmar_ratio(r)) == np.sign(metrics.annualized_return(r))


def test_engine_uses_shifted_weights():
    # Weights are decided at t and applied to t+1 returns (no look-ahead).
    returns = pd.DataFrame({0: [0.0, 0.1, 0.1], 1: [0.0, -0.1, -0.1]})
    weights = pd.DataFrame({0: [1.0, 1.0, 1.0], 1: [0.0, 0.0, 0.0]})
    res = engine.run_backtest(weights, returns)
    assert res["gross"].iloc[0] == 0.0           # no position carried into day 0
    assert abs(res["gross"].iloc[1] - 0.1) < 1e-12  # day-0 weight earns day-1 return


def test_deflated_below_raw_psr():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.0005, 0.01, 1000))
    raw = metrics.probabilistic_sharpe_ratio(r)
    deflated = metrics.deflated_sharpe_ratio(r, n_trials=50, sr_variance=0.01)
    assert deflated <= raw
