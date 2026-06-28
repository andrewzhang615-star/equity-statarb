"""Residualized reversal signals.

MVP pipeline (market residual):
  1. Market proxy = equal-weighted cross-sectional mean return each day.
  2. Per-name rolling beta = cov(ret, mkt) / var(mkt) over `estimation_window`.
  3. Residual return = ret - beta * mkt.
  4. Feed residual returns into the same short-horizon reversal logic as the raw
     baseline (buy residual losers / sell residual winners).

Winsorization (signal input only) is applied before residualizing, so one extreme
move can't distort either the market proxy or the betas. `returns_full` (realized
PnL) is never touched.

Stretch pipeline (Avellaneda & Lee 2010): PCA residuals -> cumulative residual
modeled as an OU process -> s-score with half-life filter. Stubbed below; add only
after the market- and sector-residual baselines are working end-to-end.
"""
from __future__ import annotations

import pandas as pd

from src.signals.reversal import reversal_signal, winsorize


def market_residuals(
    returns: pd.DataFrame,
    window: int,
    eligible: pd.DataFrame | None = None,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """Rolling market-model residuals: ``resid = ret - beta * mkt``.

    Market proxy = equal-weighted mean return of the **eligible (tradable)
    universe** when `eligible` is supplied, so the residualization benchmark
    matches the universe the strategy actually trades (a full-CRSP equal-weighted
    mean would be dominated by thousands of untradable microcaps). Falls back to
    the full-panel mean if `eligible` is None. Beta is a rolling cov/var over
    `window`. Fully vectorized (no per-stock loop).
    """
    mp = min_periods or max(window // 2, 20)
    if eligible is not None:
        mkt = returns.where(eligible.reindex_like(returns).fillna(False)).mean(axis=1)
    else:
        mkt = returns.mean(axis=1)
    mkt = mkt.astype("float32")                               # eligible-universe market
    ex = returns.rolling(window, min_periods=mp).mean()
    em = mkt.rolling(window, min_periods=mp).mean()
    exm = returns.mul(mkt, axis=0).rolling(window, min_periods=mp).mean()
    emm = mkt.pow(2).rolling(window, min_periods=mp).mean()
    cov = exm.sub(ex.mul(em, axis=0))
    var = emm - em.pow(2)
    beta = cov.div(var, axis=0)
    return returns.sub(beta.mul(mkt, axis=0))


def residual_reversal_signal(
    returns: pd.DataFrame, config: dict, eligible: pd.DataFrame | None = None
) -> pd.DataFrame:
    """End-to-end market-residual reversal signal (MVP).

    returns -> winsorize (signal input only) -> market residuals (vs the eligible
    universe) -> reversal.
    """
    rcfg = config["signals"]["reversal"]
    wcfg = config["signals"]["winsorize"]
    window = config["residual"]["estimation_window"]
    w = winsorize(returns, wcfg["lower"], wcfg["upper"])
    resid = market_residuals(w, window, eligible=eligible)
    return reversal_signal(resid, lookback=rcfg["lookback"], skip=rcfg["skip"], winsor=None)


# --------------------------------------------------------------------------- #
# Stretch (Avellaneda & Lee) — not part of the MVP
# --------------------------------------------------------------------------- #
def pca_residuals(returns: pd.DataFrame, n_factors: int, window: int) -> pd.DataFrame:
    """Return the residual return panel after removing `n_factors` PCs."""
    raise NotImplementedError


def ou_sscore(cum_residual: pd.DataFrame, window: int) -> pd.DataFrame:
    """Fit OU on each rolling cumulative residual and return the s-score panel."""
    raise NotImplementedError
