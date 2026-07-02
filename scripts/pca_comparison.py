"""Phase 2, Layer C: PCA(k=15) residual vs sector-LOO residual (IS, common dates).

Pre-registered decision rule (research_log.md): headline metric = net Sharpe @7bps
on COMMON valid dates (PCA needs a 252d warmup). If PCA(k=15) improves it, the
final combined candidate is PCA(k=15) + earnings exclusion; otherwise sector-LOO +
earnings exclusion. k=5 / k=30 are SENSITIVITY ONLY -- no selection from them.

Run:  python scripts/pca_comparison.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG
from src.data.load import load_eligible, load_returns_full, load_sector
from src.signals.pca import pca_residuals
from src.signals.residual import sector_residuals
from src.signals.reversal import reversal_signal, winsorize

COSTS = (2, 5, 7)


def candidate_from_resid(resid, eligible, cfg):
    rcfg, pcfg = cfg["signals"]["reversal"], cfg["portfolio"]
    sig = reversal_signal(resid, lookback=rcfg["lookback"], skip=rcfg["skip"], winsor=None)
    sig = engine.ewma_smooth(sig, pcfg["smoothing_halflife"])
    return engine.signal_to_weights(
        sig, eligible=eligible, gross_leverage=pcfg["gross_leverage"],
        max_weight=pcfg["max_weight"], market_neutral=pcfg["market_neutral"],
    )


def report(name, w, returns, mask):
    res = engine.run_backtest(w, returns, cost_bps=0.0)[mask]
    g, turn = res["gross"], res["turnover"]
    be = 1e4 * g.mean() / turn.mean()
    nets = "  ".join(f"net@{c} {metrics.sharpe_ratio(g - turn * (c / 1e4)):5.2f}" for c in COSTS)
    print(f"  {name:22s} gross {metrics.sharpe_ratio(g):5.2f} | ann {metrics.annualized_return(g) * 100:5.1f}%"
          f" | turn {turn.mean():.3f} | breakeven {be:5.1f} bps | {nets}")


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    wcfg = cfg["signals"]["winsorize"]
    w_ret = winsorize(returns, wcfg["lower"], wcfg["upper"])

    resid_sec = sector_residuals(w_ret, sector, eligible,
                                 min_peers=cfg["residual"]["sector_min_peers"])
    resid_pca, diag = pca_residuals(w_ret, eligible, window=252, n_factors=15, reestimate=21)

    print("=== Layer C: PCA(k=15) vs sector-LOO | IS, common valid dates ===")
    print(f"PCA diagnostics: estimations {len(diag)} | names/window avg {diag['n_names'].mean():.0f}"
          f" | avg coverage {diag['avg_coverage'].mean() * 100:.1f}%"
          f" | var explained (k=15) avg {diag['var_explained'].mean() * 100:.1f}%")

    first_valid = resid_pca.notna().any(axis=1).idxmax()
    mask = (returns.index >= first_valid) & (returns.index < oos)
    print(f"common window: {first_valid.date()} .. {oos.year - 1}-12-31")

    report("sector-LOO (baseline)", candidate_from_resid(resid_sec, eligible, cfg), returns, mask)
    report("PCA k=15 (candidate)", candidate_from_resid(resid_pca, eligible, cfg), returns, mask)

    print("\nsensitivity (NO selection from these):")
    for k in (5, 30):
        rk, _ = pca_residuals(w_ret, eligible, window=252, n_factors=k, reestimate=21)
        report(f"PCA k={k} (sensitivity)", candidate_from_resid(rk, eligible, cfg), returns, mask)


if __name__ == "__main__":
    main()
