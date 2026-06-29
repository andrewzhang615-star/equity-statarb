"""Cost-sensitivity of the locked candidate (sector-residual reversal + EWMA hl=5).

Net Sharpe and annualized net return as a function of the assumed per-turnover
cost. The zero-crossing is the breakeven cost. IN-SAMPLE only (holdout sealed).

Saves reports/figures/cost_sensitivity.png and prints a table.
Run:  python scripts/cost_sensitivity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.plotstyle import apply_style

apply_style()

from src.backtest import engine, metrics
from src.config import CONFIG, ROOT
from src.data.load import load_eligible, load_returns_full, load_sector
from src.portfolio.construct import candidate_weights


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)

    w = candidate_weights(returns, eligible, sector, cfg)
    res = engine.run_backtest(w, returns, cost_bps=0.0)  # gross + turnover; cost applied below
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    res = res[res.index < oos]
    gross, turn = res["gross"], res["turnover"]

    assumed = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    breakeven = 1e4 * gross.mean() / turn.mean()

    costs = np.arange(0, 15.5, 1.0)
    sharpes = []
    print(f"=== Cost sensitivity | locked candidate | IS 2000-{oos.year - 1} ===")
    print(f"avg turnover {turn.mean():.3f}/day | breakeven {breakeven:.1f} bps | assumed {assumed:.0f} bps")
    print(" cost_bps  net_sharpe  net_ann%")
    for c in costs:
        net = gross - turn * (c / 1e4)
        s, a = metrics.sharpe_ratio(net), metrics.annualized_return(net) * 100
        sharpes.append(s)
        tag = " <- assumed" if abs(c - assumed) < 0.5 else (" <- ~breakeven" if abs(c - breakeven) < 0.5 else "")
        print(f"   {c:4.0f}      {s:6.2f}     {a:6.1f}{tag}")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(costs, sharpes, marker="o")
    ax.axhline(0, color="grey", lw=0.8)
    ax.axvline(breakeven, color="green", ls="--", lw=1, label=f"breakeven {breakeven:.1f} bps")
    ax.axvline(assumed, color="red", ls="--", lw=1, label=f"assumed {assumed:.0f} bps")
    ax.set_xlabel("cost (bps per unit turnover)")
    ax.set_ylabel("net Sharpe (in-sample)")
    ax.set_title("Cost sensitivity: sector-residual reversal + EWMA hl=5")
    ax.legend()
    out = ROOT / "reports/figures/cost_sensitivity.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
