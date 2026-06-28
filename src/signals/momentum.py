"""Cross-sectional momentum stretch goal (Jegadeesh & Titman 1993).

Signal = cumulative return over the past `lookback` days, SKIPPING the most
recent `skip` days (typically ~1 month) so the momentum signal does not overlap
the short-horizon reversal signal. Demeaned cross-sectionally.

This is deliberately not part of the MVP. Add it only after raw reversal,
residualized reversal, costs, and IS/OOS robustness are complete.
"""
from __future__ import annotations

import pandas as pd


def momentum_signal(returns: pd.DataFrame, lookback: int = 252, skip: int = 21) -> pd.DataFrame:
    """Past-return momentum with a skip window, demeaned cross-sectionally."""
    raise NotImplementedError
