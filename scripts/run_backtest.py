"""Raw reversal baseline: data -> signal -> weights -> backtest -> metrics.

Run from the repo root:  python scripts/run_backtest.py

Reports IN-SAMPLE metrics only (2000 .. oos_start-1). The 2019-2024 holdout is
sealed for the final evaluation and is deliberately NOT evaluated here.
"""
from __future__ import annotations

import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG
from src.data.load import load_eligible, load_returns_full
from src.signals.reversal import reversal_signal


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)

    rcfg, wcfg, pcfg = cfg["signals"]["reversal"], cfg["signals"]["winsorize"], cfg["portfolio"]
    signal = reversal_signal(
        returns, lookback=rcfg["lookback"], skip=rcfg["skip"],
        winsor=(wcfg["lower"], wcfg["upper"]),
    )
    weights = engine.signal_to_weights(
        signal, eligible=eligible,
        gross_leverage=pcfg["gross_leverage"], max_weight=pcfg["max_weight"],
        market_neutral=pcfg["market_neutral"],
    )
    cost_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    res = engine.run_backtest(weights, returns, cost_bps=cost_bps)

    # IN-SAMPLE ONLY -- do not look at the holdout.
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    is_res = res[res.index < oos]
    is_w = weights[weights.index < oos]
    g, n = is_res["gross"], is_res["net"]

    print(f"=== Raw {rcfg['lookback']}-day reversal | IN-SAMPLE 2000..{oos.year - 1} ===")
    print(f"days: {len(is_res):,} | cost: {cost_bps:.1f} bps per unit turnover "
          f"| avg names/day: {int((is_w != 0).sum(axis=1).mean())}")
    print(f"GROSS  sharpe {metrics.sharpe_ratio(g):5.2f} | ann {metrics.annualized_return(g) * 100:6.1f}% "
          f"| vol {metrics.annualized_vol(g) * 100:4.1f}% | maxDD {metrics.max_drawdown(g) * 100:6.1f}%")
    print(f"NET    sharpe {metrics.sharpe_ratio(n):5.2f} | ann {metrics.annualized_return(n) * 100:6.1f}% "
          f"| vol {metrics.annualized_vol(n) * 100:4.1f}% | maxDD {metrics.max_drawdown(n) * 100:6.1f}%")
    print(f"avg daily turnover (sum|dw|): {is_res['turnover'].mean():.3f}")
    breakeven = 1e4 * g.mean() / is_res["turnover"].mean()
    print(f"BREAKEVEN cost: {breakeven:.1f} bps per unit turnover  (net Sharpe -> 0)")


if __name__ == "__main__":
    main()
