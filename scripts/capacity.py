"""Capacity analysis: net Sharpe vs deployed AUM under square-root market impact.

Locked candidate (sector-residual reversal + EWMA hl=5), IN-SAMPLE only. Adds
square-root impact ON TOP of the linear cost floor:

    impact_i = eta * sigma_i * sqrt(|dw_i|*AUM / ADV$_i)

over eta in {0.3, 0.6, 1.0} and AUM from $10M to $10B (log-spaced). Reports a
capacity curve plus participation diagnostics (a curve without participation
context can look cleaner than reality). sigma and ADV$ are trailing, lagged one
day (no look-ahead).

Saves reports/figures/capacity.png. Run:  python scripts/capacity.py
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
from src.data.load import advdollar_panel, load_eligible, load_returns_full, load_sector
from src.execution.impact import participation_stats, sqrt_impact_base
from src.portfolio.construct import candidate_weights
from src.signals.reversal import winsorize


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)

    w = candidate_weights(returns, eligible, sector, cfg)
    res = engine.run_backtest(w, returns, cost_bps=0.0)

    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    is_is = returns.index < oos
    gross = res["gross"][is_is]
    turnover = res["turnover"][is_is]
    dw = (w - w.shift(1))[is_is]

    # trailing, lagged-one-day estimates (no look-ahead)
    wcfg = cfg["signals"]["winsorize"]
    vol = winsorize(returns, wcfg["lower"], wcfg["upper"]).rolling(60, min_periods=20).std().shift(1)[is_is]
    adv = advdollar_panel(cfg).reindex_like(returns)[is_is]
    base = sqrt_impact_base(dw, vol, adv)

    floor_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    linear = turnover * (floor_bps / 1e4)
    aum_grid = np.logspace(7, 10, 7)         # $10M .. $10B
    etas = [0.3, 0.6, 1.0]

    base_sharpe = metrics.sharpe_ratio(gross - linear)
    print(f"=== Capacity | locked candidate | IS 2000-{oos.year - 1} | floor {floor_bps:.0f} bps ===")
    print(f"net Sharpe with NO size impact (small-AUM limit): {base_sharpe:.2f}")

    print("\nparticipation (trade$/ADV$) over traded name-days:")
    print("    AUM        avg     p95      max    %>1%  %>5%  %>10%")
    for aum in aum_grid:
        s = participation_stats(dw, adv, aum)
        print(f"  ${aum/1e6:7.0f}M  {s['avg']*100:5.2f}%  {s['p95']*100:5.2f}%  {s['max']*100:6.1f}%  "
              f"{s['pct>1%']:4.1f}  {s['pct>5%']:4.1f}  {s['pct>10%']:4.1f}")

    print("\nnet Sharpe by AUM x eta:")
    print("    AUM       eta=0.3  eta=0.6  eta=1.0")
    curves = {e: [] for e in etas}
    for aum in aum_grid:
        row = []
        for e in etas:
            net = gross - linear - e * np.sqrt(aum) * base
            sh = metrics.sharpe_ratio(net)
            curves[e].append(sh)
            row.append(sh)
        print(f"  ${aum/1e6:7.0f}M    {row[0]:6.2f}   {row[1]:6.2f}   {row[2]:6.2f}")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = ["black", "red", "blue"]  # eta = 0.3 / 0.6 / 1.0
    for e, c in zip(etas, colors):
        ax.plot(aum_grid / 1e6, curves[e], color=c, label=f"eta={e}")
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("deployed AUM ($M, log scale)")
    ax.set_ylabel("net Sharpe (in-sample)")
    ax.set_title("Capacity: net Sharpe vs AUM under sqrt impact")
    ax.legend()
    out = ROOT / "reports/figures/capacity.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
