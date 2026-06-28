"""Liquidity-bucket robustness: re-run the locked candidate restricted to the top
500 / 1000 / 1500 names by trailing dollar volume.

Restricting eligibility shrinks BOTH the traded universe AND the sector
leave-one-out peer set (eligibility drives both inside candidate_weights), so each
bucket is a self-consistent "trade only top-N" strategy. Tests whether the edge
relies on less-liquid names. IS only; 2019-2024 holdout sealed.

Run:  python scripts/liquidity_buckets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG, ROOT
from src.data.load import apply_delisting_returns, build_eligibility, load_returns_full, load_sector
from src.portfolio.construct import candidate_weights


def main() -> None:
    cfg = CONFIG
    dcfg, delcfg = cfg["data"], cfg["delisting"]
    cost_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]

    returns = load_returns_full().astype("float32")
    sector = load_sector().reindex_like(returns)
    # daily (with delist_event) is needed to rebuild eligibility at each universe size
    daily = pd.read_parquet(ROOT / dcfg["raw_path"])
    daily = apply_delisting_returns(daily, pd.read_parquet(ROOT / dcfg["delist_path"]), delcfg)
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])

    print(f"=== Liquidity buckets | locked candidate | IS 2000-{oos.year - 1} | {cost_bps:.0f} bps ===")
    print("  universe   names/day  gross   net   net_ann%  breakeven")
    for n in (500, 1000, 1500):
        elig = build_eligibility(daily, {**dcfg, "universe_size": n}).reindex_like(returns).fillna(False)
        w = candidate_weights(returns, elig, sector, cfg)
        res = engine.run_backtest(w, returns, cost_bps=cost_bps)
        res, wis = res[res.index < oos], w[w.index < oos]
        g, net = res["gross"], res["net"]
        be = 1e4 * g.mean() / res["turnover"].mean()
        names = int((wis != 0).sum(axis=1).mean())
        print(f"  top {n:4d}   {names:6d}     {metrics.sharpe_ratio(g):5.2f}  {metrics.sharpe_ratio(net):5.2f}  "
              f"{metrics.annualized_return(net) * 100:6.1f}    {be:5.1f}")


if __name__ == "__main__":
    main()
