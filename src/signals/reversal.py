"""Short-horizon reversal (Lehmann 1990; Lo & MacKinlay 1990).

Signal = negative of the recent cumulative return (buy losers / sell winners).

Returns are WINSORIZED before forming the signal so a single extreme move (e.g. a
penny-stock spike) cannot dominate the cross-section. Winsorization touches the
SIGNAL INPUT ONLY -- never realized PnL (`returns_full`), which must keep the true
returns or we would be sanitizing the backtest's wins and losses. The functions
here never mutate their input.
"""
from __future__ import annotations

import pandas as pd


def winsorize(returns: pd.DataFrame, lower: float = -0.20, upper: float = 0.20) -> pd.DataFrame:
    """Clip returns into [lower, upper]. For SIGNAL formation only (returns a copy)."""
    return returns.clip(lower=lower, upper=upper)


def reversal_signal(
    returns: pd.DataFrame,
    lookback: int = 5,
    skip: int = 0,
    winsor: tuple[float, float] | None = (-0.20, 0.20),
) -> pd.DataFrame:
    """Negative trailing (summed) return over the lookback window.

    `returns` is the never-masked PnL panel; we winsorize a COPY for the signal and
    never touch the input. Cross-sectional demeaning / neutralization happens later
    in ``engine.signal_to_weights``.
    """
    r = winsorize(returns, *winsor) if winsor else returns
    past = r.rolling(lookback, min_periods=lookback).sum()
    if skip:
        past = past.shift(skip)
    return -past
