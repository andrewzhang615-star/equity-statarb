"""Portfolio construction.

`candidate_weights` builds the LOCKED candidate strategy end-to-end:
sector-residual reversal (leave-one-out) -> EWMA smoothing (turnover control) ->
dollar-neutral, capped weights. Cost-sensitivity, capacity, and the eventual OOS
run all call this, so the strategy definition lives in exactly one place.
"""
from __future__ import annotations

import pandas as pd

from src.backtest import engine
from src.signals.residual import sector_reversal_signal


def candidate_weights(
    returns: pd.DataFrame,
    eligible: pd.DataFrame,
    sector: pd.DataFrame,
    config: dict,
    weight_eligible: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Locked candidate: sector-residual reversal + EWMA smoothing -> weights.

    `weight_eligible` (optional) restricts which names may RECEIVE weight without
    changing the signal computation (residuals/peers still use `eligible`). Used
    by Phase 2 exclusion variants, e.g. earnings-in-window names forced to zero.
    """
    pcfg = config["portfolio"]
    signal = sector_reversal_signal(returns, config, sector, eligible)
    signal = engine.ewma_smooth(signal, pcfg["smoothing_halflife"])
    return engine.signal_to_weights(
        signal, eligible=eligible if weight_eligible is None else weight_eligible,
        gross_leverage=pcfg["gross_leverage"], max_weight=pcfg["max_weight"],
        market_neutral=pcfg["market_neutral"],
    )
