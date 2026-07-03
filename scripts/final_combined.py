"""Phase 2 finale: the final combined candidate -- PCA(k=15) + earnings exclusion.

Pre-specified by the Layer C decision rule after PCA(k=15) beat sector-LOO on the
headline metric. Reports the full 2x2 grid (residual method x earnings exclusion)
on COMMON valid dates so every attribution is visible. The combined candidate is
DSR candidate #3.

Run:  python scripts/final_combined.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG, ROOT
from src.data.earnings import earnings_event_panel, earnings_in_window, map_announcements_to_permnos
from src.data.load import load_eligible, load_returns_full, load_sector
from src.signals.pca import pca_residuals
from src.signals.residual import sector_residuals
from src.signals.reversal import reversal_signal, winsorize

COSTS = (2, 5, 7)


def weights_from(resid, eligible, cfg, weight_eligible=None):
    rcfg, pcfg = cfg["signals"]["reversal"], cfg["portfolio"]
    sig = reversal_signal(resid, lookback=rcfg["lookback"], skip=rcfg["skip"], winsor=None)
    sig = engine.ewma_smooth(sig, pcfg["smoothing_halflife"])
    return engine.signal_to_weights(
        sig, eligible=eligible if weight_eligible is None else weight_eligible,
        gross_leverage=pcfg["gross_leverage"], max_weight=pcfg["max_weight"],
        market_neutral=pcfg["market_neutral"],
    )


def report(name, w, returns, mask):
    res = engine.run_backtest(w, returns, cost_bps=0.0)[mask]
    g, turn = res["gross"], res["turnover"]
    be = 1e4 * g.mean() / turn.mean()
    nets = "  ".join(f"net@{c} {metrics.sharpe_ratio(g - turn * (c / 1e4)):5.2f}" for c in COSTS)
    print(f"  {name:26s} gross {metrics.sharpe_ratio(g):5.2f} | ann {metrics.annualized_return(g) * 100:5.1f}%"
          f" | turn {turn.mean():.3f} | breakeven {be:5.1f} bps | {nets}")


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    wcfg, ecfg = cfg["signals"]["winsorize"], cfg["signals"]["earnings"]
    w_ret = winsorize(returns, wcfg["lower"], wcfg["upper"])

    resid_sec = sector_residuals(w_ret, sector, eligible,
                                 min_peers=cfg["residual"]["sector_min_peers"])
    resid_pca, _ = pca_residuals(w_ret, eligible, window=252, n_factors=15, reestimate=21)

    rdq = pd.read_parquet(ROOT / cfg["data"]["earnings_path"])
    links = pd.read_parquet(ROOT / cfg["data"]["ccm_link_path"])
    flag = earnings_in_window(
        earnings_event_panel(map_announcements_to_permnos(rdq, links), returns.index, returns.columns),
        window=ecfg["window"], extend=ecfg["extend"],
    )
    we = eligible & ~flag

    first_valid = resid_pca.notna().any(axis=1).idxmax()
    mask = (returns.index >= first_valid) & (returns.index < oos)
    print(f"=== Phase 2 final: residual x earnings-exclusion grid | IS common dates "
          f"({first_valid.date()} .. {oos.year - 1}) ===")
    report("sector-LOO", weights_from(resid_sec, eligible, cfg), returns, mask)
    report("sector-LOO + earn-excl", weights_from(resid_sec, eligible, cfg, we), returns, mask)
    report("PCA k=15", weights_from(resid_pca, eligible, cfg), returns, mask)
    report("PCA k=15 + earn-excl (FINAL)", weights_from(resid_pca, eligible, cfg, we), returns, mask)


if __name__ == "__main__":
    main()
