"""Market impact & capacity (square-root law).

Per-name impact of trading ``trade$ = |dw|*AUM`` dollars in name i, in return units:

    impact_i = eta * sigma_i * sqrt(trade$_i / ADV$_i)

Portfolio impact cost per day = ``sum_i |dw_i| * impact_i``. Substituting trade$ and
factoring AUM/eta out makes the (AUM, eta) sweep cheap:

    cost_t(AUM, eta) = eta * sqrt(AUM) * base_t,
    base_t = sum_i |dw_i| * sigma_i * sqrt(|dw_i| / ADV$_i)

so ``base_t`` is computed once and scaled across the grid. sigma (daily vol) and
ADV$ are trailing, lagged one day (no look-ahead) -- see scripts/capacity.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sqrt_impact_base(dweights: pd.DataFrame, vol: pd.DataFrame, advdollar: pd.DataFrame) -> pd.Series:
    """AUM/eta-free daily base of the square-root impact cost (return units).

    cost_t(AUM, eta) = eta * sqrt(AUM) * base_t.
    """
    dw = dweights.abs()
    per_name = dw * vol * np.sqrt(dw / advdollar)
    # NaN (untraded names, or missing vol/ADV$ during warmup) are skipped by the
    # sum. That slightly understates cost, but is negligible here (~0.001-0.002%
    # of traded weight has missing vol/ADV$).
    return per_name.sum(axis=1)


def participation_stats(dweights: pd.DataFrame, advdollar: pd.DataFrame, aum: float) -> dict:
    """Distribution of participation (trade$ / ADV$) over traded name-days."""
    dw = dweights.abs()
    part = (dw * aum / advdollar).where(dw > 0).to_numpy()
    part = part[np.isfinite(part)]
    return {
        "avg": float(np.mean(part)),
        "p95": float(np.quantile(part, 0.95)),
        "max": float(np.max(part)),
        "pct>1%": float(np.mean(part > 0.01) * 100),
        "pct>5%": float(np.mean(part > 0.05) * 100),
        "pct>10%": float(np.mean(part > 0.10) * 100),
    }
