"""Regenerate the report figure set in one consistent academic style.

These figures are descriptive only: they summarize locked Phase 1 / Phase 2
results and do not enter the trial ledger.

Outputs in reports/figures:
  decile_monotonicity.png   - signal monotonicity across deciles
  cost_sensitivity.png      - net Sharpe vs assumed cost
  capacity.png              - net Sharpe vs AUM under square-root impact
  rolling_breakeven.png     - rolling 3-year break-even cost
  oos_equity.png            - full-sample net equity curve
  earnings_eventtime.png    - clean vs earnings-window event-time behavior
  pca_scree.png             - PCA cumulative variance explained
  participation_cap.png     - ADV position-cap deployment diagnostic

Run:  python scripts/paper_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from src.plotstyle import COLORS, apply_style

apply_style()

from src.backtest import engine, metrics
from src.config import CONFIG, ROOT
from src.data.earnings import earnings_event_panel, earnings_in_window, map_announcements_to_permnos
from src.data.load import advdollar_panel, load_eligible, load_returns_full, load_sector
from src.execution.impact import sqrt_impact_base
from src.portfolio.construct import candidate_weights
from src.signals.residual import sector_residuals
from src.signals.reversal import reversal_signal, winsorize

FIG = ROOT / "reports/figures"
FIGSIZE = (6.0, 4.0)


def _finish(fig, ax, name: str) -> None:
    ax.tick_params(axis="both", which="major", length=3)
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=150)
    plt.close(fig)
    print(f"saved {name}")


def _candidate_results(returns, eligible, sector, cfg, cost_bps: float = 0.0) -> pd.DataFrame:
    w = candidate_weights(returns, eligible, sector, cfg)
    return engine.run_backtest(w, returns, cost_bps=cost_bps)


def fig_decile_monotonicity(resid, eligible, cfg, is_mask) -> None:
    rcfg = cfg["signals"]["reversal"]
    sig = reversal_signal(resid, lookback=rcfg["lookback"], skip=rcfg["skip"], winsor=None)
    valid = eligible & sig.notna()
    pct = sig.where(valid).rank(axis=1, pct=True)
    decile = np.ceil(pct * 10).clip(1, 10)
    fwd1 = resid.shift(-1)

    means = []
    D = decile[is_mask].to_numpy(dtype="float32")
    F = fwd1[is_mask].to_numpy(dtype="float32")
    for d in range(1, 11):
        sel = (D == d) & ~np.isnan(F)
        means.append(1e4 * np.nanmean(F[sel]))

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.bar(range(1, 11), means, color=COLORS["secondary"], edgecolor=COLORS["primary"], width=0.72)
    ax.axhline(0, color=COLORS["muted"], lw=0.8)
    ax.set_xticks(range(1, 11))
    ax.set_xlabel("Signal decile")
    ax.set_ylabel("Next-day residual return (bps)")
    ax.set_title("Forward return by reversal-signal decile")
    _finish(fig, ax, "decile_monotonicity.png")


def fig_cost_sensitivity(returns, eligible, sector, cfg, is_mask) -> None:
    res = _candidate_results(returns, eligible, sector, cfg, cost_bps=0.0)[is_mask]
    gross, turn = res["gross"], res["turnover"]
    assumed = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    breakeven = 1e4 * gross.mean() / turn.mean()
    costs = np.arange(0, 15.5, 1.0)
    sharpes = [metrics.sharpe_ratio(gross - turn * (c / 1e4)) for c in costs]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(costs, sharpes, color=COLORS["primary"], lw=1.3)
    ax.axhline(0, color=COLORS["muted"], lw=0.8)
    ax.axvline(assumed, color=COLORS["accent"], ls="--", lw=1.0, label=f"assumed cost ({assumed:.0f} bps)")
    ax.axvline(breakeven, color=COLORS["muted"], ls="--", lw=1.0, label=f"break-even ({breakeven:.1f} bps)")
    ax.set_xlabel("Cost per unit turnover (bps)")
    ax.set_ylabel("Net Sharpe")
    ax.set_title("Cost sensitivity")
    ax.legend(loc="lower left")
    _finish(fig, ax, "cost_sensitivity.png")


def fig_capacity(returns, eligible, sector, cfg, is_mask) -> None:
    w = candidate_weights(returns, eligible, sector, cfg)
    res = engine.run_backtest(w, returns, cost_bps=0.0)
    gross = res["gross"][is_mask]
    turnover = res["turnover"][is_mask]
    dw = (w - w.shift(1))[is_mask]
    wcfg = cfg["signals"]["winsorize"]
    vol = winsorize(returns, wcfg["lower"], wcfg["upper"]).rolling(60, min_periods=20).std().shift(1)[is_mask]
    adv = advdollar_panel(cfg).reindex_like(returns)[is_mask]
    base = sqrt_impact_base(dw, vol, adv)
    floor_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    linear = turnover * (floor_bps / 1e4)
    aum_grid = np.logspace(7, 10, 7)
    etas = [(0.3, COLORS["primary"]), (0.6, COLORS["secondary"]), (1.0, COLORS["accent"])]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for eta, color in etas:
        sharpes = [metrics.sharpe_ratio(gross - linear - eta * np.sqrt(aum) * base) for aum in aum_grid]
        ax.plot(aum_grid / 1e6, sharpes, color=color, lw=1.3, label=fr"$\eta={eta}$")
    ax.axhline(0, color=COLORS["muted"], lw=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("Deployed AUM ($M, log scale)")
    ax.set_ylabel("Net Sharpe")
    ax.set_title("Capacity under square-root impact")
    ax.legend(loc="lower left")
    _finish(fig, ax, "capacity.png")


def fig_participation_cap(returns, eligible, sector, cfg, is_mask) -> None:
    w = candidate_weights(returns, eligible, sector, cfg)
    wcfg = cfg["signals"]["winsorize"]
    vol = winsorize(returns, wcfg["lower"], wcfg["upper"]).rolling(60, min_periods=20).std().shift(1)[is_mask]
    adv_full = advdollar_panel(cfg).reindex_like(returns)
    adv = adv_full[is_mask]
    floor_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    eta = 0.6
    aum_grid = np.logspace(7, 10, 7)
    caps = [
        (None, "no cap", COLORS["primary"]),
        (0.05, "5% cap", COLORS["secondary"]),
        (0.10, "10% cap", COLORS["accent"]),
        (0.25, "25% cap", COLORS["accent2"]),
    ]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for cap, label, color in caps:
        sharpes = []
        for aum in aum_grid:
            w_use = w if cap is None else engine.apply_position_cap(w, adv_full, aum, cap)
            res = engine.run_backtest(w_use, returns, cost_bps=0.0)
            gross = res["gross"][is_mask]
            turnover = res["turnover"][is_mask]
            dw = (w_use - w_use.shift(1))[is_mask]
            base = sqrt_impact_base(dw, vol, adv)
            net = gross - turnover * (floor_bps / 1e4) - eta * np.sqrt(aum) * base
            sharpes.append(metrics.sharpe_ratio(net))
        ax.plot(aum_grid / 1e6, sharpes, color=color, lw=1.3, label=label)

    ax.axhline(0, color=COLORS["muted"], lw=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("Deployed AUM ($M, log scale)")
    ax.set_ylabel(r"Net Sharpe ($\eta=0.6$)")
    ax.set_title("Position-cap capacity comparison")
    ax.legend(loc="lower left")
    _finish(fig, ax, "participation_cap.png")


def fig_rolling_breakeven(returns, eligible, sector, cfg) -> None:
    res = _candidate_results(returns, eligible, sector, cfg, cost_bps=0.0)
    window = 756
    be = 1e4 * res["gross"].rolling(window, min_periods=504).mean() \
        / res["turnover"].rolling(window, min_periods=504).mean()
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    assumed = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(be.index, be.values, color=COLORS["primary"], lw=1.1)
    ax.axhline(assumed, color=COLORS["accent"], ls="--", lw=1.0, label=f"assumed cost ({assumed:.0f} bps)")
    ax.axhline(0, color=COLORS["muted"], lw=0.8)
    ax.axvline(oos, color=COLORS["muted"], ls=":", lw=1.1)
    ax.set_xlabel("Date")
    ax.set_ylabel("Break-even cost (bps)")
    ax.set_title("Rolling 3-year break-even cost")
    ax.legend(loc="lower left")
    _finish(fig, ax, "rolling_breakeven.png")


def fig_oos_equity(returns, eligible, sector, cfg) -> None:
    cost_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    res = _candidate_results(returns, eligible, sector, cfg, cost_bps=cost_bps)
    eq = (1 + res["net"]).cumprod()
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(eq.index, eq.values, color=COLORS["primary"], lw=1.0)
    ax.axvline(oos, color=COLORS["muted"], ls=":", lw=1.1)
    ax.set_yscale("log")
    yticks = np.arange(0.9, 1.8, 0.1)
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{y:.1f}" for y in yticks])
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.set_xlabel("Date")
    ax.set_ylabel("Net equity (log scale)")
    ax.set_title("Net equity at 7 bps cost")
    ax.text(
        oos + pd.DateOffset(months=3), 0.97, "OOS start",
        transform=ax.get_xaxis_transform(),
        color=COLORS["secondary"], fontsize=9, ha="left", va="top",
    )
    _finish(fig, ax, "oos_equity.png")


def fig_earnings_eventtime(returns, resid, eligible, cfg, is_mask) -> None:
    rcfg, ecfg = cfg["signals"]["reversal"], cfg["signals"]["earnings"]
    sig = reversal_signal(resid, lookback=rcfg["lookback"], skip=rcfg["skip"], winsor=None)
    rdq = pd.read_parquet(ROOT / cfg["data"]["earnings_path"])
    links = pd.read_parquet(ROOT / cfg["data"]["ccm_link_path"])
    flag = earnings_in_window(
        earnings_event_panel(map_announcements_to_permnos(rdq, links), returns.index, returns.columns),
        window=ecfg["window"], extend=ecfg["extend"],
    )
    valid = eligible & sig.notna()
    direction = np.sign(sig)

    horizons = range(1, 11)
    curves = {"Clean moves": valid & ~flag, "Earnings-window moves": valid & flag}
    out = {name: [] for name in curves}
    for h in horizons:
        fwd = resid.rolling(h).sum().shift(-h)
        pnl = direction * fwd
        for name, m in curves.items():
            v = pnl.where(m)[is_mask].to_numpy(dtype="float32")
            out[name].append(1e4 * np.nanmean(v))

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(list(horizons), out["Clean moves"], color=COLORS["primary"], lw=1.2, label="Clean moves")
    ax.plot(list(horizons), out["Earnings-window moves"], color=COLORS["accent"], ls="--", lw=1.2,
            label="Earnings-window moves")
    ax.axhline(0, color=COLORS["muted"], lw=0.8)
    ax.set_xticks(list(horizons))
    ax.set_xlabel("Days after signal formation")
    ax.set_ylabel("Cumulative residual PnL (bps)")
    ax.set_title("Post-signal residual drift")
    ax.legend(loc="upper left")
    _finish(fig, ax, "earnings_eventtime.png")


def fig_pca_scree(returns, eligible, cfg) -> None:
    wcfg = cfg["signals"]["winsorize"]
    R = winsorize(returns, wcfg["lower"], wcfg["upper"]).to_numpy(dtype="float64")
    E = eligible.to_numpy(dtype=bool)
    window, reestimate, kmax = 252, 21, 40
    curves = []
    for t0 in range(window - 1, R.shape[0], reestimate):
        win = R[t0 - window + 1: t0 + 1]
        cov = 1.0 - np.isnan(win).mean(axis=0)
        use = E[t0] & (cov >= 0.60)
        mu = np.nanmean(win[:, use], axis=0)
        sd = np.nanstd(win[:, use], axis=0)
        ok = sd > 1e-12
        X = (win[:, use][:, ok] - mu[ok]) / sd[ok]
        X[np.isnan(X)] = 0.0
        if X.shape[1] <= kmax:
            continue
        S = np.linalg.svd(X, compute_uv=False)
        ratio = np.cumsum(S**2) / (S**2).sum()
        curves.append(ratio[:kmax])
    avg = np.mean(curves, axis=0)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ks = np.arange(1, kmax + 1)
    ax.plot(ks, 100 * avg, color=COLORS["primary"], lw=1.2)
    ax.axvline(15, color=COLORS["accent"], ls="--", lw=1.0, label=f"k = 15 ({100 * avg[14]:.0f}%)")
    ax.set_xlabel("Number of principal components")
    ax.set_ylabel("Cumulative variance explained (%)")
    ax.set_title("PCA variance explained")
    ax.legend(loc="upper left")
    _finish(fig, ax, "pca_scree.png")


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    is_mask = returns.index < oos
    wcfg = cfg["signals"]["winsorize"]
    resid = sector_residuals(winsorize(returns, wcfg["lower"], wcfg["upper"]), sector, eligible,
                             min_peers=cfg["residual"]["sector_min_peers"])

    FIG.mkdir(parents=True, exist_ok=True)
    fig_decile_monotonicity(resid, eligible, cfg, is_mask)
    fig_cost_sensitivity(returns, eligible, sector, cfg, is_mask)
    fig_capacity(returns, eligible, sector, cfg, is_mask)
    fig_participation_cap(returns, eligible, sector, cfg, is_mask)
    fig_rolling_breakeven(returns, eligible, sector, cfg)
    fig_oos_equity(returns, eligible, sector, cfg)
    fig_earnings_eventtime(returns, resid, eligible, cfg, is_mask)
    fig_pca_scree(returns, eligible, cfg)


if __name__ == "__main__":
    main()
