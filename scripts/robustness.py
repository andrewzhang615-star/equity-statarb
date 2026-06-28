"""Pre-OOS robustness checks on the locked candidate (IN-SAMPLE 2000-2018 only).

(1) Subperiod stability: 2000-2006, 2007-2012, 2013-2018 -- does the edge survive
    the 2008 crisis and the post-2010 "reversal decay" era?
(2) Long-leg vs short-leg attribution -- is the edge symmetric, or one-sided?

The 2019-2024 holdout stays sealed. Run:  python scripts/robustness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG
from src.data.load import load_eligible, load_returns_full, load_sector
from src.portfolio.construct import candidate_weights


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)
    cost_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]

    w = candidate_weights(returns, eligible, sector, cfg)
    res = engine.run_backtest(w, returns, cost_bps=cost_bps)
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    res = res[res.index < oos]

    print(f"=== Robustness | locked candidate | IS 2000-{oos.year - 1} | {cost_bps:.0f} bps ===")

    print("\n(1) Subperiod stability")
    print("  period       gross Sh  net Sh   net ann%  breakeven")
    for lo, hi in [(2000, 2006), (2007, 2012), (2013, 2018)]:
        sub = res[(res.index.year >= lo) & (res.index.year <= hi)]
        g, n = sub["gross"], sub["net"]
        be = 1e4 * g.mean() / sub["turnover"].mean()
        print(f"  {lo}-{hi}    {metrics.sharpe_ratio(g):6.2f}   {metrics.sharpe_ratio(n):6.2f}   "
              f"{metrics.annualized_return(n) * 100:6.1f}    {be:5.1f} bps")

    print("\n(2) Long vs short leg (gross contribution, IS)")
    applied = w.shift(1)
    R = returns.fillna(0.0)
    long_c = (applied.clip(lower=0) * R).sum(axis=1).reindex(res.index)
    short_c = (applied.clip(upper=0) * R).sum(axis=1).reindex(res.index)
    for label, leg in [("long  (buy resid losers)", long_c), ("short (sell resid winners)", short_c)]:
        print(f"  {label:26s}: ann {metrics.annualized_return(leg) * 100:5.1f}%  |  "
              f"sharpe {metrics.sharpe_ratio(leg):5.2f}")
    print("  (each leg carries directional exposure; the relative split is the signal.)")


if __name__ == "__main__":
    main()
