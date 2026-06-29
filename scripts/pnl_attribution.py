"""PnL attribution + short-side realism + crash episodes (locked candidate, IS only).

(a) Concentration: gross PnL by name (top-N share, breadth), by year, by sector.
(b) Short-side realism: short-leg PnL split by price and by liquidity (ADV) bucket
    -- are the short profits in low-price / illiquid (hard-to-borrow) names?
(c) Crash episodes: worst drawdown window + worst months vs the concurrent market,
    to substantiate the "struggles when selloffs persist" (crash-risk) reading
    rather than asserting it off the single-day up/down split.

Holdout sealed. Run from repo root:  python scripts/pnl_attribution.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import numpy as np
import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG, ROOT
from src.data.load import load_eligible, load_returns_full, load_sector
from src.portfolio.construct import candidate_weights


def _bucketed_sum(contrib, key, edges, labels):
    """Sum `contrib` cells grouped by which bin of `key` they fall in (flattened)."""
    c = contrib.to_numpy(dtype="float64", na_value=np.nan).ravel()
    k = key.to_numpy(dtype="float64", na_value=np.nan).ravel()
    m = np.isfinite(c) & np.isfinite(k) & (c != 0)
    c, k = c[m], k[m]
    idx = np.digitize(k, edges)
    return {labels[i]: c[idx == i].sum() for i in range(len(labels))}


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)
    cost_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    is_mask = returns.index < oos

    w = candidate_weights(returns, eligible, sector, cfg)
    applied = w.shift(1)
    R = returns.fillna(0.0)
    contrib = (applied * R)[is_mask]                 # per-name daily PnL contribution
    gross_daily = contrib.sum(axis=1)
    total = gross_daily.sum()

    # ---------- (a) concentration ----------
    print(f"=== (a) PnL concentration | IS 2000-{oos.year - 1} | total gross {total:.2f} (cum. return units) ===")
    per_name = contrib.sum(axis=0).sort_values(ascending=False)
    for k in (10, 50):
        print(f"  top {k} names: {per_name.head(k).sum() / total * 100:5.1f}% of total gross PnL")
    print(f"  names net-positive: {(per_name > 0).sum()} | net-negative: {(per_name < 0).sum()} (breadth)")

    print("  by year (gross PnL):")
    yr = gross_daily.groupby(gross_daily.index.year).sum()
    print("    " + "  ".join(f"{y}:{v:+.2f}" for y, v in yr.items()))

    # point-in-time sector attribution: group each day's contribution by that day's sector
    cflat = contrib.to_numpy(dtype="float64", na_value=np.nan).ravel()
    sflat = sector[is_mask].to_numpy(dtype="float64", na_value=np.nan).ravel()
    m = np.isfinite(cflat) & np.isfinite(sflat) & (cflat != 0)
    by_sector = pd.Series(cflat[m]).groupby(sflat[m].astype("int64")).sum().sort_values(ascending=False)
    print("  top/bottom sectors (2-digit SIC, point-in-time, gross PnL):")
    print("    top:    " + "  ".join(f"{int(s)}:{v:+.2f}" for s, v in by_sector.head(5).items()))
    print("    bottom: " + "  ".join(f"{int(s)}:{v:+.2f}" for s, v in by_sector.tail(5).items()))

    # ---------- (b) short-side realism ----------
    pv = pd.read_parquet(ROOT / cfg["data"]["raw_path"], columns=["permno", "date", "prc", "vol"])
    pv["aprc"] = pv["prc"].abs()
    pv["dvol"] = pv["aprc"] * pv["vol"]
    price = pv.pivot(index="date", columns="permno", values="aprc").reindex_like(returns)[is_mask]
    adv = (pv.pivot(index="date", columns="permno", values="dvol")
           .rolling(cfg["data"]["adv_window"], min_periods=cfg["data"]["adv_min_periods"]).mean()
           .shift(1).reindex_like(returns)[is_mask])
    short_contrib = (applied.clip(upper=0) * R)[is_mask]

    print("\n=== (b) Short-side realism (short-leg gross PnL by bucket) ===")
    by_price = _bucketed_sum(short_contrib, price, [10, 25, 50], ["$5-10", "$10-25", "$25-50", "$50+"])
    print("  by price:     " + "  ".join(f"{k}:{v:+.2f}" for k, v in by_price.items()))
    q = [float(x) for x in adv.stack().quantile([0.25, 0.5, 0.75]).values]
    by_adv = _bucketed_sum(short_contrib, adv, q, ["ADV q1(low)", "q2", "q3", "q4(high)"])
    print("  by liquidity: " + "  ".join(f"{k}:{v:+.2f}" for k, v in by_adv.items()))

    # ---------- (c) crash episodes ----------
    res = engine.run_backtest(w, returns, cost_bps=cost_bps)
    net = res["net"][is_mask]
    mkt = returns.where(eligible).mean(axis=1)[is_mask]
    eq = (1 + net).cumprod()
    dd = eq / eq.cummax() - 1.0
    trough = dd.idxmin()
    peak = eq.loc[:trough].idxmax()
    mkt_window = (1 + mkt.loc[peak:trough]).prod() - 1
    print("\n=== (c) Crash / drawdown episodes (net, IS) ===")
    print(f"  worst drawdown: {dd.min() * 100:.1f}%  ({peak.date()} -> {trough.date()}); "
          f"market over window: {mkt_window * 100:+.1f}%")
    net_m = (1 + net).resample("ME").prod() - 1
    mkt_m = (1 + mkt).resample("ME").prod() - 1
    print("  worst 5 months (net | concurrent market):")
    for d, v in net_m.nsmallest(5).items():
        print(f"    {d.strftime('%Y-%m')}: net {v * 100:+5.1f}%  | market {mkt_m.get(d, np.nan) * 100:+5.1f}%")


if __name__ == "__main__":
    main()
