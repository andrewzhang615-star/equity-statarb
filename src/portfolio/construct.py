"""Portfolio construction: combine signals and map to weights.

MVP: map a single residual-reversal signal to neutralized weights.

Stretch: blend residual reversal with momentum or additional signals using
weights from config. Later: factor/beta neutralization beyond simple demeaning.

TODO: implement after the raw and residualized reversal signals exist.
"""
from __future__ import annotations

import pandas as pd


def combine_signals(signals: dict[str, pd.DataFrame], weights: dict[str, float]) -> pd.DataFrame:
    """Z-score each signal cross-sectionally, then blend by `weights`."""
    raise NotImplementedError
