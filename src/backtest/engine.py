"""Vectorized cross-sectional backtest engine.

Two defenses against fooling ourselves live here:

1. **Look-ahead:** weights are SHIFTED one period before they earn returns, so a
   position only ever uses information available at the prior close.

2. **The disappearing-loser leak:** PnL is computed against ``returns_full`` (the
   unmasked total-return panel, delisting returns included). Eligibility/price/
   liquidity filters enter ONLY through ``signal_to_weights(eligible=...)`` — they
   gate which names may receive new weight, they never erase a held name's return.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def signal_to_weights(
    signal: pd.DataFrame,
    eligible: pd.DataFrame | None = None,
    gross_leverage: float = 1.0,
    max_weight: float | None = None,
    market_neutral: bool = True,
) -> pd.DataFrame:
    """Map a cross-sectional signal to dollar-neutral weights.

    If ``eligible`` is given, only eligible names can receive weight; the
    cross-sectional demean and gross-leverage scaling are taken over the eligible
    set each day.
    """
    s = signal.copy()
    if eligible is not None:
        s = s.where(eligible.reindex_like(s).fillna(False))
    if market_neutral:
        s = s.sub(s.mean(axis=1), axis=0)
    gross = s.abs().sum(axis=1)
    w = s.div(gross.replace(0.0, np.nan), axis=0) * gross_leverage
    if max_weight is not None:
        w = w.clip(-max_weight, max_weight)
        if market_neutral:
            # Clipping can re-introduce a small net exposure; restore dollar-
            # neutrality. The resulting cap overage from re-demeaning is negligible.
            w = w.sub(w.mean(axis=1), axis=0)
    return w.fillna(0.0)


def run_backtest(
    weights: pd.DataFrame,
    returns_full: pd.DataFrame,
    cost_bps: float = 0.0,
) -> pd.DataFrame:
    """Run target weights against the FULL (unmasked) return panel.

    Returns a DataFrame with columns: gross, cost, net, turnover.
    Missing non-delisting returns are treated as 0 for a held name (carry); a
    delisting return is a real value in ``returns_full`` and is therefore
    realized, not skipped.
    """
    w = weights.reindex_like(returns_full).fillna(0.0)
    applied = w.shift(1).fillna(0.0)  # decided at prior close -> no look-ahead
    gross_ret = (applied * returns_full.fillna(0.0)).sum(axis=1)
    turn = (w - w.shift(1)).abs().sum(axis=1).fillna(0.0)
    cost = turn * (cost_bps / 1e4)
    net_ret = gross_ret - cost
    return pd.DataFrame(
        {"gross": gross_ret, "cost": cost, "net": net_ret, "turnover": turn}
    )


# --------------------------------------------------------------------------- #
# Turnover-reduction levers (vectorized)
# --------------------------------------------------------------------------- #
def ewma_smooth(signal: pd.DataFrame, halflife: float | None) -> pd.DataFrame:
    """EWMA-smooth a signal across time so positions are stickier (less churn).

    `halflife` is in trading days; None/<=0 returns the signal unchanged.
    """
    if not halflife or halflife <= 0:
        return signal
    return signal.ewm(halflife=halflife, min_periods=1).mean()


def apply_holding_period(weights: pd.DataFrame, k: int) -> pd.DataFrame:
    """Rebalance only every `k` days; hold weights between rebalances.

    Trades on a coarser grid to cut turnover. k<=1 returns weights unchanged.

    Caveat (exploration helper): holds a position until the next rebalance even if
    the target went to zero (e.g. a name delists / leaves the universe mid-period).
    The committed candidate uses EWMA smoothing, not this; if a holding-period
    strategy is ever used seriously, force exits on delist/ineligible days.
    """
    if k <= 1:
        return weights
    held = weights.copy()
    non_rebalance = np.where((np.arange(len(held)) % k) != 0)[0]
    held.iloc[non_rebalance] = np.nan      # blank the off-grid days...
    return held.ffill().fillna(0.0)        # ...and carry the last rebalance forward


def apply_position_cap(
    weights: pd.DataFrame,
    advdollar: pd.DataFrame,
    aum: float,
    cap_frac: float,
    market_neutral: bool = True,
) -> pd.DataFrame:
    """Cap each name's position to a fraction of its ADV$: |wᵢ| ≤ cap_frac·ADV$ᵢ/AUM,
    then re-neutralize. Bounds the thin-name impact tail.

    This is a vectorized POSITION/target cap, not a true (path-dependent) "never
    trade >X% ADV/day" trade cap. In a broad book the re-neutralization offset is
    tiny so caps effectively hold; in a narrow book it can relax them slightly.
    """
    max_w = (cap_frac * advdollar / aum).reindex_like(weights)
    max_w = max_w.where(max_w.notna(), np.inf)       # missing ADV -> no cap
    capped = weights.clip(lower=-max_w, upper=max_w)
    if market_neutral:
        # Re-neutralize over TRADED names only, and keep untraded names at exactly
        # zero. (A blanket demean would leak tiny weight onto non-eligible names
        # with zero/NaN ADV, blowing up participation/impact.)
        traded = weights != 0
        capped = capped.sub(capped.where(traded).mean(axis=1), axis=0).where(traded, 0.0)
    return capped
