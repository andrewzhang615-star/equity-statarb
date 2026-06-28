"""Market impact & capacity.

MVP: build a simple capacity curve using turnover, average daily dollar volume,
and a conservative linear/slippage cost assumption. This is enough to answer:
"how much deployed capital can the signal plausibly absorb before net Sharpe
collapses?"

Stretch: refine the model with an Almgren-Chriss-inspired impact framework.

Square-root impact (per trade, in return terms):
    cost ~= spread/2  +  eta * sigma * sqrt(Q / ADV)
where Q is shares traded, ADV is average daily volume, sigma is daily vol, and
eta is an impact coefficient calibrated from the literature (~0.1-1).

capacity_curve: re-run the strategy at increasing AUM and plot net Sharpe vs.
capital to find where impact erodes the edge -- the project's HFT-flavored
contribution.

TODO: implement the simple capacity curve first; keep square-root impact as the
second version.
"""
from __future__ import annotations

import pandas as pd


def square_root_impact(
    trade_fraction_adv: pd.DataFrame,
    daily_vol: pd.DataFrame,
    spread: pd.DataFrame | float,
    eta: float = 0.1,
) -> pd.DataFrame:
    """Per-name impact cost (in return units) for a given trade size vs. ADV."""
    raise NotImplementedError


def capacity_curve(signal: pd.DataFrame, returns: pd.DataFrame, aum_grid, config: dict):
    """Net Sharpe as a function of deployed capital."""
    raise NotImplementedError
