"""Reversal baselines: raw vs. market-residual.

data -> signal -> weights -> backtest -> metrics, reported IN-SAMPLE ONLY
(2000 .. oos_start-1). The 2019-2024 holdout is sealed and deliberately NOT
evaluated here.

Run from the repo root:  python scripts/run_backtest.py
"""
from __future__ import annotations

import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG
from src.data.load import load_eligible, load_returns_full
from src.signals.residual import residual_reversal_signal
from src.signals.reversal import reversal_signal


def evaluate(name: str, signal, returns, eligible, cfg) -> dict:
    pcfg = cfg["portfolio"]
    weights = engine.signal_to_weights(
        signal, eligible=eligible,
        gross_leverage=pcfg["gross_leverage"], max_weight=pcfg["max_weight"],
        market_neutral=pcfg["market_neutral"],
    )
    cost_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    res = engine.run_backtest(weights, returns, cost_bps=cost_bps)

    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    res, w = res[res.index < oos], weights[weights.index < oos]
    g, n = res["gross"], res["net"]
    breakeven = 1e4 * g.mean() / res["turnover"].mean()

    print(f"\n=== {name} | IN-SAMPLE 2000..{oos.year - 1} ===")
    print(f"  GROSS  sharpe {metrics.sharpe_ratio(g):5.2f} | ann {metrics.annualized_return(g) * 100:6.1f}% "
          f"| vol {metrics.annualized_vol(g) * 100:4.1f}% | maxDD {metrics.max_drawdown(g) * 100:6.1f}%")
    print(f"  NET    sharpe {metrics.sharpe_ratio(n):5.2f} | ann {metrics.annualized_return(n) * 100:6.1f}% "
          f"| maxDD {metrics.max_drawdown(n) * 100:6.1f}%  (at {cost_bps:.1f} bps/turn)")
    print(f"  turnover {res['turnover'].mean():.3f}/day | BREAKEVEN {breakeven:.1f} bps/turn")
    return {"name": name, "gross": metrics.sharpe_ratio(g), "net": metrics.sharpe_ratio(n),
            "turnover": res["turnover"].mean(), "breakeven": breakeven}


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    rcfg, wcfg = cfg["signals"]["reversal"], cfg["signals"]["winsorize"]

    raw = reversal_signal(returns, lookback=rcfg["lookback"], skip=rcfg["skip"],
                          winsor=(wcfg["lower"], wcfg["upper"]))
    evaluate(f"Raw {rcfg['lookback']}d reversal", raw, returns, eligible, cfg)

    mres = residual_reversal_signal(returns, cfg, eligible=eligible)
    evaluate(f"Market-residual {rcfg['lookback']}d reversal", mres, returns, eligible, cfg)


if __name__ == "__main__":
    main()
