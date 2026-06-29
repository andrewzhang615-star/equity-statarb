"""THE ONE-SHOT OUT-OF-SAMPLE EVALUATION (2019-2024).

Runs the FROZEN candidate (sector-residual 5d reversal + EWMA hl=5, top-1000) and
reports IN-SAMPLE vs OUT-OF-SAMPLE side by side. No parameters are chosen here --
everything comes from config.yaml / the frozen spec. Run ONCE.

Outputs: IS-vs-OOS metric table, a deflated Sharpe on the IS result (accounting for
the configs we tried), and an equity-curve figure marking the IS/OOS boundary.

Run:  python scripts/oos_evaluation.py
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

from src.backtest import engine, metrics
from src.config import CONFIG, ROOT
from src.data.load import load_eligible, load_returns_full, load_sector
from src.portfolio.construct import candidate_weights

# Annualized IS net Sharpes of every strategy config we evaluated (from the
# research-log ledger) -- used for the deflated Sharpe trial adjustment.
TRIAL_NET_SHARPES = [
    -0.39,  # raw reversal
    -0.48,  # market-residual (full-CRSP proxy)
    -0.39,  # market-residual (eligible proxy)
    -0.33,  # sector-residual LOO
    0.28, 0.33, 0.34, 0.33,  # EWMA hl = 2, 3, 5, 10
    0.04, 0.03, 0.28, 0.09,  # holding period k = 2, 3, 5, 10
]


def segment_report(name: str, res: pd.DataFrame) -> str:
    g, net, turn = res["gross"], res["net"], res["turnover"]
    nets = {c: metrics.sharpe_ratio(g - turn * (c / 1e4)) for c in (2, 5, 7)}
    be = 1e4 * g.mean() / turn.mean()
    return (f"  {name:12s} days {len(res):5d} | gross Sh {metrics.sharpe_ratio(g):5.2f} "
            f"| net@2 {nets[2]:5.2f}  net@5 {nets[5]:5.2f}  net@7 {nets[7]:5.2f} "
            f"| ann@7 {metrics.annualized_return(net) * 100:5.1f}% | maxDD {metrics.max_drawdown(net) * 100:5.1f}% "
            f"| breakeven {be:4.1f} bps | turn {turn.mean():.2f}")


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)
    cost_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]

    w = candidate_weights(returns, eligible, sector, cfg)
    res = engine.run_backtest(w, returns, cost_bps=cost_bps)
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    is_res, oos_res = res[res.index < oos], res[res.index >= oos]

    dsr = metrics.deflated_sharpe_ratio(is_res["net"], n_trials=len(TRIAL_NET_SHARPES),
                                        trial_sharpes=TRIAL_NET_SHARPES)
    lines = [
        f"=== ONE-SHOT OOS | frozen candidate | split at {oos.date()} | floor {cost_bps:.0f} bps ===",
        segment_report("IN-SAMPLE", is_res),
        segment_report("OUT-SAMPLE", oos_res),
        f"\nDeflated Sharpe (IS net, {len(TRIAL_NET_SHARPES)} trials): "
        f"P(true Sharpe>0 after selection) = {dsr:.2f}",
    ]

    eq = (1 + res["net"]).cumprod()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(eq.index, eq.values)
    ax.axvline(oos, color="red", ls="--", lw=1, label=f"OOS start {oos.date()}")
    ax.set_yscale("log")
    ax.set_xlabel("date")
    ax.set_ylabel("net equity (log, 7 bps)")
    ax.set_title("Frozen candidate: net equity curve (IS | OOS)")
    ax.legend()
    fig_out = ROOT / "reports/figures/oos_equity.png"
    fig.tight_layout()
    fig.savefig(fig_out, dpi=120)
    lines.append(f"saved {fig_out}")

    report = "\n".join(lines)
    print(report)
    summary_path = ROOT / "reports/oos_summary.txt"
    summary_path.write_text(report + "\n")
    print(f"saved {summary_path}")


if __name__ == "__main__":
    main()
