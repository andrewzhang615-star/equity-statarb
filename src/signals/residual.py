"""Residualized reversal signals.

MVP pipeline:
  1. Estimate each stock's exposure to a common market return over a rolling
     window.
  2. Subtract the fitted common component from each stock's return.
  3. Feed those residual returns into the same short-horizon reversal logic used
     by the raw baseline.

Stretch pipeline (Avellaneda & Lee 2010):

Pipeline, per rolling estimation window:
  1. Residualize each stock's returns against common factors (PCA components or
     sector ETFs).  resid = ret - beta @ factor_returns
  2. Form the cumulative residual X_t and fit an OU process:
        dX = kappa * (m - X) dt + sigma dW
     via the AR(1) of X_t (X_{t+1} = a + b X_t + eps, kappa = -ln(b)).
  3. s-score = (X - m) / sigma_eq, where sigma_eq = sigma / sqrt(2 kappa).
  4. Keep only names whose half-life (ln2 / kappa) is within
     [ou_min_halflife, ou_max_halflife] -- fast enough to be tradable.

Trade (handled in portfolio construction): go long when s < -entry, short when
s > +entry, flatten when |s| < exit.

TODO: implement the market-residual MVP first. Add PCA/OU only after the raw and
market-residual baselines are working end-to-end.
"""
from __future__ import annotations

import pandas as pd


def market_residuals(returns: pd.DataFrame, window: int) -> pd.DataFrame:
    """Return rolling market-model residual returns for the MVP."""
    raise NotImplementedError


def pca_residuals(returns: pd.DataFrame, n_factors: int, window: int) -> pd.DataFrame:
    """Return the residual return panel after removing `n_factors` PCs."""
    raise NotImplementedError


def ou_sscore(cum_residual: pd.DataFrame, window: int) -> pd.DataFrame:
    """Fit OU on each rolling cumulative residual and return the s-score panel."""
    raise NotImplementedError


def residual_reversal_signal(returns: pd.DataFrame, config: dict) -> pd.DataFrame:
    """End-to-end residualized reversal signal.

    MVP: returns -> market residuals -> short-horizon reversal.
    Stretch: returns -> PCA residuals -> OU s-score -> threshold signal.
    """
    raise NotImplementedError
