"""Turnover-reduction sweep on the best signal so far (sector-residual reversal).

The breakeven analysis says residualization improved the per-trade edge but
turnover (~0.63/day) keeps the strategy under the cost line. This sweeps two
vectorized turnover levers and reports how net Sharpe / breakeven respond:

  - EWMA signal smoothing (halflife in days)
  - holding period (rebalance every k days)

IN-SAMPLE only (2000 .. oos_start-1); the holdout stays sealed. Every row here is
a tuned config -> log them to the trial ledger for the deflated-Sharpe count.

Run from the repo root:  python scripts/turnover_sweep.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG
from src.data.load import load_eligible, load_returns_full, load_sector
from src.signals.residual import sector_reversal_signal


def evaluate(signal, returns, eligible, cfg, halflife=None, hold=1) -> dict:
    pcfg = cfg["portfolio"]
    sig = engine.ewma_smooth(signal, halflife)
    w = engine.signal_to_weights(
        sig, eligible=eligible,
        gross_leverage=pcfg["gross_leverage"], max_weight=pcfg["max_weight"],
        market_neutral=pcfg["market_neutral"],
    )
    w = engine.apply_holding_period(w, hold)
    cost_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    res = engine.run_backtest(w, returns, cost_bps=cost_bps)
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    res = res[res.index < oos]
    g, n = res["gross"], res["net"]
    return {
        "gross": metrics.sharpe_ratio(g), "net": metrics.sharpe_ratio(n),
        "turnover": res["turnover"].mean(), "breakeven": 1e4 * g.mean() / res["turnover"].mean(),
    }


def _row(label, m):
    print(f"  {label:14s}: net {m['net']:5.2f} | gross {m['gross']:5.2f} "
          f"| turn {m['turnover']:.3f} | breakeven {m['breakeven']:4.1f} bps")


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)
    cost_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    signal = sector_reversal_signal(returns, cfg, sector, eligible)  # best signal so far

    print(f"=== Turnover sweep on sector-residual reversal | IS 2000-2018 | cost {cost_bps:.0f} bps ===")
    _row("base", evaluate(signal, returns, eligible, cfg))
    print("-- EWMA smoothing (halflife days) --")
    for h in (2, 3, 5, 10):
        _row(f"smooth hl={h}", evaluate(signal, returns, eligible, cfg, halflife=h))
    print("-- Holding period (rebalance every k days) --")
    for k in (2, 3, 5, 10):
        _row(f"hold k={k}", evaluate(signal, returns, eligible, cfg, hold=k))


if __name__ == "__main__":
    main()
