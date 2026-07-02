"""PCA / latent-factor residualization (Phase 2, Layer C; Avellaneda & Lee 2010).

Pre-registered design (research_log.md):
- Correlation-based PCA on winsorized returns, standardized per name by the
  trailing-window mean/std so high-vol names don't dominate the factors.
- Rolling 252d window, re-estimated every 21 trading days; loadings applied
  forward until the next estimation (stale between estimations -> no look-ahead;
  the estimation date itself uses same-day returns, consistent with sector-LOO).
- Estimation universe: names eligible at the estimation date with >= 60%
  non-missing coverage in-window. Missing standardized returns are set to 0
  (= NEUTRAL/mean return; matrix-completion convention, reported via coverage
  diagnostics). Names outside the universe get NaN residuals, never fabricated.
- Economy SVD on the T x N standardized window (T < N): right singular vectors
  are the correlation eigenvectors. Residual = (I - VV')r_std, de-standardized.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def pca_residuals(
    returns: pd.DataFrame,
    eligible: pd.DataFrame,
    window: int = 252,
    n_factors: int = 15,
    reestimate: int = 21,
    min_coverage: float = 0.60,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rolling-PCA residual panel plus per-estimation diagnostics.

    Returns (residuals, diagnostics); diagnostics rows are per estimation date
    with n_names, avg in-window coverage, and variance explained by the top k.
    """
    R = returns.to_numpy(dtype="float64")
    E = eligible.reindex_like(returns).fillna(False).to_numpy(dtype=bool)
    T, N = R.shape
    resid = np.full((T, N), np.nan, dtype="float64")
    diags = []

    for t0 in range(window - 1, T, reestimate):
        win = R[t0 - window + 1 : t0 + 1]                      # (window x N), ends at t0
        cov = 1.0 - np.isnan(win).mean(axis=0)
        use = E[t0] & (cov >= min_coverage)
        mu = np.nanmean(win[:, use], axis=0)
        sd = np.nanstd(win[:, use], axis=0)
        ok = sd > 1e-12                                        # drop zero-vol names
        use_idx = np.flatnonzero(use)[ok]
        mu, sd = mu[ok], sd[ok]
        if len(use_idx) <= n_factors:
            continue

        X = (win[:, use_idx] - mu) / sd
        X[np.isnan(X)] = 0.0                                   # missing -> neutral
        _, S, Vt = np.linalg.svd(X, full_matrices=False)       # economy SVD
        V = Vt[:n_factors].T                                   # (n_use x k) eigenvectors
        var_explained = float((S[:n_factors] ** 2).sum() / (S ** 2).sum())

        # apply loadings to the block [t0 .. t0+reestimate-1] (stale forward)
        t1 = min(t0 + reestimate, T)
        blk = R[t0:t1][:, use_idx]
        missing = np.isnan(blk)
        Xb = (blk - mu) / sd
        Xb[missing] = 0.0
        res_std = Xb - (Xb @ V) @ V.T                          # (I - VV') per day
        res_raw = res_std * sd
        res_raw[missing] = np.nan                              # no return -> no residual
        resid[t0:t1][:, use_idx] = res_raw                     # basic slice view -> writes through

        diags.append({"date": returns.index[t0], "n_names": len(use_idx),
                      "avg_coverage": float(cov[use].mean()), "var_explained": var_explained})

    return (
        pd.DataFrame(resid, index=returns.index, columns=returns.columns),
        pd.DataFrame(diags).set_index("date") if diags else pd.DataFrame(),
    )
