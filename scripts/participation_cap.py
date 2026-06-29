"""Participation (position) cap: does capping per-name positions extend capacity?

The uncapped capacity curve collapsed because a thin-name TAIL hit >100% of ADV at
larger AUM. Here we cap each name's position to a fraction of its ADV$
(|wᵢ| ≤ cap_frac·ADV$ᵢ/AUM, then re-neutralize) and re-run the capacity curve. This
is a vectorized POSITION cap, not a true path-dependent trade cap (documented).

Shows net Sharpe vs AUM for cap in {none, 5%, 10%, 25%} (10% main) at eta=0.6, plus
how the participation tail shrinks. IN-SAMPLE only; holdout sealed.

Run:  python scripts/participation_cap.py
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
from src.data.load import advdollar_panel, load_eligible, load_returns_full, load_sector
from src.execution.impact import participation_stats, sqrt_impact_base
from src.portfolio.construct import candidate_weights
from src.signals.reversal import winsorize

ETA = 0.6  # mid impact scenario for the cap comparison
CAPS = [None, 0.05, 0.10, 0.25]


def net_sharpe_and_tail(w_use, returns, vol, adv, aum, floor_bps, is_mask):
    res = engine.run_backtest(w_use, returns, cost_bps=0.0)
    gross = res["gross"][is_mask]
    turnover = res["turnover"][is_mask]
    dw = (w_use - w_use.shift(1))[is_mask]
    base = sqrt_impact_base(dw, vol, adv)
    net = gross - turnover * (floor_bps / 1e4) - ETA * np.sqrt(aum) * base
    return metrics.sharpe_ratio(net), participation_stats(dw, adv, aum)["max"]


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)
    floor_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    is_mask = returns.index < oos

    w = candidate_weights(returns, eligible, sector, cfg)
    wcfg = cfg["signals"]["winsorize"]
    vol = winsorize(returns, wcfg["lower"], wcfg["upper"]).rolling(60, min_periods=20).std().shift(1)[is_mask]
    adv = advdollar_panel(cfg).reindex_like(returns)[is_mask]
    aum_grid = np.logspace(7, 10, 7)  # $10M .. $10B

    print(f"=== Participation (position) cap | IS 2000-{oos.year - 1} | floor {floor_bps:.0f} bps, eta {ETA} ===")
    sharpes = {c: [] for c in CAPS}
    tails = {c: [] for c in CAPS}
    for aum in aum_grid:
        for c in CAPS:
            w_use = w if c is None else engine.apply_position_cap(w, adv.reindex_like(returns), aum, c)
            sh, tail = net_sharpe_and_tail(w_use, returns, vol, adv, aum, floor_bps, is_mask)
            sharpes[c].append(sh)
            tails[c].append(tail)

    def label(c):
        return "uncapped" if c is None else f"cap {int(c*100)}%"

    print("\nnet Sharpe by AUM x cap:")
    print("    AUM      " + "  ".join(f"{label(c):>9s}" for c in CAPS))
    for i, aum in enumerate(aum_grid):
        print(f"  ${aum/1e6:7.0f}M  " + "  ".join(f"{sharpes[c][i]:9.2f}" for c in CAPS))

    print("\nmax participation (trade/ADV) by AUM x cap:")
    print("    AUM      " + "  ".join(f"{label(c):>9s}" for c in CAPS))
    for i, aum in enumerate(aum_grid):
        print(f"  ${aum/1e6:7.0f}M  " + "  ".join(f"{tails[c][i]*100:8.1f}%" for c in CAPS))

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for c in CAPS:
        ax.plot(aum_grid / 1e6, sharpes[c], marker="o", label=label(c))
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("deployed AUM ($M, log scale)")
    ax.set_ylabel(f"net Sharpe (IS, eta={ETA})")
    ax.set_title("Capacity with position cap (cap = % of ADV held)")
    ax.legend()
    out = ROOT / "reports/figures/participation_cap.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
