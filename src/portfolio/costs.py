"""Transaction-cost models.

linear_cost: simple per-turnover bps (commissions + fixed slippage).
impact_cost: size-dependent slippage feeding the capacity analysis (see
             execution/impact.py for the square-root impact model).

TODO: implement during the portfolio/execution phase.
"""
from __future__ import annotations

import pandas as pd


def linear_cost(turnover: pd.Series, bps: float) -> pd.Series:
    """Per-period cost = turnover * bps/1e4."""
    return turnover * (bps / 1e4)


def impact_cost(trade_dollars: pd.DataFrame, adv_dollars: pd.DataFrame, **kwargs) -> pd.Series:
    """Size-dependent slippage; see execution.impact.square_root_impact."""
    raise NotImplementedError
