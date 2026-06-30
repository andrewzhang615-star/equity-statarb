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
"""
from __future__ import annotations

import numpy as np
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


def sector_residuals(
    returns: pd.DataFrame,
    sector: pd.DataFrame,
    eligible: pd.DataFrame,
    min_peers: int = 5,
) -> pd.DataFrame:
    """Leave-one-out sector demeaning over the eligible universe.

    ``resid_i,t = ret_i,t - mean_{j != i, same sector, eligible}(ret_j,t)``.

    Leave-one-out (excluding the stock from its own benchmark) avoids a name
    mechanically pulling its sector mean toward itself -- which matters most in
    small sectors. A stock with fewer than `min_peers` same-sector eligible peers
    that day gets NaN (it does not trade). Sectors are point-in-time (no
    look-ahead). Vectorized with one pass per distinct sector code.

    Timing: the residual at day t uses same-day (cross-sectional) peer returns,
    all known at close t; the reversal signal is formed at close t and traded at
    t+1 via the engine's weight shift. Same-day peers are contemporaneous, not
    look-ahead.
    """
    R = returns.to_numpy(dtype="float32")
    S = sector.reindex_like(returns).to_numpy(dtype="float32")
    E = eligible.reindex_like(returns).fillna(False).to_numpy(dtype=bool)
    valid = E & ~np.isnan(R) & ~np.isnan(S)

    resid = np.full(R.shape, np.nan, dtype="float32")
    for k in np.unique(S[valid]):
        member = (S == k) & valid
        cnt = member.sum(axis=1)                       # names in sector k per day
        denom = cnt - 1                                # peers excluding self
        rsum = np.where(member, R, 0.0).sum(axis=1)    # sector return sum per day
        with np.errstate(invalid="ignore", divide="ignore"):
            loo = (rsum[:, None] - R) / denom[:, None]  # leave-one-out mean
        assign = member & (denom >= min_peers)[:, None]
        resid[assign] = (R - loo)[assign]
    return pd.DataFrame(resid, index=returns.index, columns=returns.columns)


def sector_reversal_signal(
    returns: pd.DataFrame, config: dict, sector: pd.DataFrame, eligible: pd.DataFrame
) -> pd.DataFrame:
    """returns -> winsorize -> leave-one-out sector residuals -> reversal."""
    rcfg = config["signals"]["reversal"]
    wcfg = config["signals"]["winsorize"]
    mp = config["residual"]["sector_min_peers"]
    w = winsorize(returns, wcfg["lower"], wcfg["upper"])
    resid = sector_residuals(w, sector, eligible, min_peers=mp)
    return reversal_signal(resid, lookback=rcfg["lookback"], skip=rcfg["skip"], winsor=None)
