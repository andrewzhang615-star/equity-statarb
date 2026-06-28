"""Pre-OOS robustness checks on the locked candidate (IN-SAMPLE 2000-2018 only).

(1) Subperiod stability x cost: 2000-06 / 07-12 / 13-18 at 2/5/7/10 bps -- turns
    the decay result into a clean execution story.
(2) Long vs short leg: portfolio contribution AND a CAPM-style beta-adjusted alpha
    (is the long-side edge real alpha, or just market exposure?).

The 2019-2024 holdout stays sealed. Run:  python scripts/robustness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import numpy as np
import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG
from src.data.load import load_eligible, load_returns_full, load_sector
from src.portfolio.construct import candidate_weights

COSTS = (2, 5, 7, 10)


def _subperiod_row(label, sub):
    g, turn = sub["gross"], sub["turnover"]
    be = 1e4 * g.mean() / turn.mean()
    nets = [metrics.sharpe_ratio(g - turn * (c / 1e4)) for c in COSTS]
    nets_str = "  ".join(f"{s:6.2f}" for s in nets)
    print(f"  {label:11s}  {metrics.sharpe_ratio(g):5.2f}   {be:5.1f}    {nets_str}")


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)

    w = candidate_weights(returns, eligible, sector, cfg)
    res = engine.run_backtest(w, returns, cost_bps=0.0)  # gross + turnover; costs applied below
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    res = res[res.index < oos]

    print(f"=== Robustness | locked candidate | IS 2000-{oos.year - 1} ===")
    print("\n(1) Subperiod stability x cost  (net Sharpe at 2/5/7/10 bps)")
    print(f"  period      gross  break|   net@2   net@5   net@7  net@10")
    for lo, hi in [(2000, 2006), (2007, 2012), (2013, 2018)]:
        _subperiod_row(f"{lo}-{hi}", res[(res.index.year >= lo) & (res.index.year <= hi)])
    _subperiod_row("ALL IS", res)

    print("\n(2) Long vs short leg: portfolio contribution + beta-adjusted alpha (IS)")
    applied = w.shift(1)
    R = returns.fillna(0.0)
    mkt = returns.where(eligible).mean(axis=1).reindex(res.index).fillna(0.0)
    legs = {
        "long  (buy resid losers)": (applied.clip(lower=0) * R).sum(axis=1).reindex(res.index),
        "short (sell resid winners)": (applied.clip(upper=0) * R).sum(axis=1).reindex(res.index),
    }
    print("  leg                          contrib_ann   beta   alpha_ann    IR")
    for label, leg in legs.items():
        beta = leg.cov(mkt) / mkt.var()
        alpha_d = leg.mean() - beta * mkt.mean()
        resid = leg - (alpha_d + beta * mkt)
        ir = alpha_d / resid.std() * np.sqrt(252) if resid.std() > 0 else np.nan
        print(f"  {label:27s}  {metrics.annualized_return(leg) * 100:6.1f}%   {beta:+.2f}  "
              f"{alpha_d * 252 * 100:6.1f}%   {ir:5.2f}")
    print("  (contribution carries market exposure; alpha_ann/IR strip it out via CAPM.)")


if __name__ == "__main__":
    main()
