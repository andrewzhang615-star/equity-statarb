"""Abnormal volume (Phase 2, Layer A).

AV_{i,t} = mean dollar volume over the signal window (t-window+1 .. t, known at
close t) divided by the trailing `base_window` mean ending BEFORE that window
(shifted by `window`, so numerator and denominator never overlap).

AV ~ 1 means the recent move happened on normal volume; AV << 1 on unusually low
volume (candidate liquidity dislocation); AV >> 1 on unusually high volume
(candidate informed move). Timing matches the reversal signal exactly -- both use
data through close t -- so the engine's one-day weight shift remains the single
look-ahead defense.
"""
from __future__ import annotations

import pandas as pd


def abnormal_volume(
    dollar_volume: pd.DataFrame,
    window: int = 5,
    base_window: int = 60,
    min_base: int = 30,
) -> pd.DataFrame:
    """Ratio of signal-window mean dollar volume to the trailing non-overlapping base."""
    win = dollar_volume.rolling(window, min_periods=window).mean()
    base = dollar_volume.rolling(base_window, min_periods=min_base).mean().shift(window)
    return win / base
