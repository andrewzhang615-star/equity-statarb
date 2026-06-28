"""Short-horizon reversal (Lehmann 1990; Lo & MacKinlay 1990).

Signal = negative of the recent cumulative return, demeaned cross-sectionally
(buy losers / sell winners). Caveat from the literature: much raw short-horizon
reversal is bid-ask bounce and may not survive realistic spreads -- which is
exactly what the execution layer is built to test.

TODO: implement first as the raw MVP signal.
"""
from __future__ import annotations

import pandas as pd


def reversal_signal(returns: pd.DataFrame, lookback: int = 5, skip: int = 0) -> pd.DataFrame:
    """Negative cumulative return over [t-lookback-skip, t-skip], demeaned."""
    raise NotImplementedError
