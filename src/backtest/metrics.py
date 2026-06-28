"""Performance metrics.

Standard set (Sharpe, IR, drawdown, Calmar, turnover) plus the **deflated
Sharpe ratio** (Bailey & Lopez de Prado 2014), which adjusts an observed Sharpe
for the number of strategy variants tried, return skew/kurtosis, and sample
length -- giving the probability the true Sharpe exceeds a benchmark.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

TRADING_DAYS = 252
EULER_MASCHERONI = 0.5772156649015329


def _clean(returns) -> pd.Series:
    return pd.Series(returns).dropna()


def annualized_return(returns, periods: int = TRADING_DAYS) -> float:
    r = _clean(returns)
    if len(r) == 0:
        return np.nan
    return (1 + r).prod() ** (periods / len(r)) - 1


def annualized_vol(returns, periods: int = TRADING_DAYS) -> float:
    return _clean(returns).std(ddof=1) * np.sqrt(periods)


def sharpe_ratio(returns, rf: float = 0.0, periods: int = TRADING_DAYS) -> float:
    r = _clean(returns) - rf / periods
    sd = r.std(ddof=1)
    return np.nan if sd == 0 else r.mean() / sd * np.sqrt(periods)


def information_ratio(returns, benchmark=0.0, periods: int = TRADING_DAYS) -> float:
    r = _clean(returns)
    b = benchmark if np.isscalar(benchmark) else pd.Series(benchmark).reindex(r.index).fillna(0.0)
    active = r - b
    sd = active.std(ddof=1)
    return np.nan if sd == 0 else active.mean() / sd * np.sqrt(periods)


def drawdown_series(returns) -> pd.Series:
    eq = (1 + _clean(returns)).cumprod()
    return eq / eq.cummax() - 1.0


def max_drawdown(returns) -> float:
    dd = drawdown_series(returns)
    return dd.min() if len(dd) else np.nan


def calmar_ratio(returns, periods: int = TRADING_DAYS) -> float:
    mdd = max_drawdown(returns)
    return np.nan if not mdd else annualized_return(returns, periods) / abs(mdd)


def average_turnover(weights: pd.DataFrame) -> float:
    """Mean one-sided turnover per period (sum of abs(delta weight) across names)."""
    return weights.fillna(0.0).diff().abs().sum(axis=1).mean()


def probabilistic_sharpe_ratio(
    returns, sr_benchmark: float = 0.0, periods: int = TRADING_DAYS
) -> float:
    """P(true Sharpe > sr_benchmark), correcting for skew & kurtosis.

    Sharpe inputs are annualized; converted to per-period internally.
    """
    r = _clean(returns)
    n = len(r)
    if n < 3:
        return np.nan
    sr = sharpe_ratio(r, periods=periods) / np.sqrt(periods)
    srb = sr_benchmark / np.sqrt(periods)
    skew = stats.skew(r)
    kurt = stats.kurtosis(r, fisher=False)  # non-excess kurtosis
    denom = np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr**2)
    z = (sr - srb) * np.sqrt(n - 1) / denom
    return float(stats.norm.cdf(z))


def deflated_sharpe_ratio(
    returns,
    n_trials: int,
    sr_variance: float | None = None,
    trial_sharpes=None,
    periods: int = TRADING_DAYS,
) -> float:
    """Deflated Sharpe ratio.

    Either pass ``sr_variance`` (variance of *annualized* Sharpes across trials)
    or ``trial_sharpes`` (the annualized Sharpes themselves). ``n_trials`` is the
    number of strategy configurations you evaluated.
    """
    if sr_variance is None:
        if trial_sharpes is None:
            raise ValueError("Provide sr_variance or trial_sharpes")
        sr_variance = np.var([s / np.sqrt(periods) for s in trial_sharpes], ddof=1)
    n = n_trials
    expected_max = np.sqrt(sr_variance) * (
        (1 - EULER_MASCHERONI) * stats.norm.ppf(1 - 1 / n)
        + EULER_MASCHERONI * stats.norm.ppf(1 - 1 / (n * np.e))
    )
    return probabilistic_sharpe_ratio(
        returns, sr_benchmark=expected_max * np.sqrt(periods), periods=periods
    )


def summary(returns, weights: pd.DataFrame | None = None, periods: int = TRADING_DAYS) -> dict:
    """One-stop performance summary for a return stream."""
    out = {
        "ann_return": annualized_return(returns, periods),
        "ann_vol": annualized_vol(returns, periods),
        "sharpe": sharpe_ratio(returns, periods=periods),
        "max_drawdown": max_drawdown(returns),
        "calmar": calmar_ratio(returns, periods),
    }
    if weights is not None:
        out["avg_turnover"] = average_turnover(weights)
    return out
