"""Phase 2 endgame: labeled spent-holdout sanity check + Phase 2 deflated Sharpe.

(1) The FINAL combined candidate (PCA k=15 + earnings exclusion) evaluated on
    2019-2024. **This period is a SPENT holdout** -- it was unsealed for the
    Phase 1 one-shot test -- so it is reported as a labeled sanity check only,
    never as fresh out-of-sample evidence. The true fresh holdout (2025+) is
    pending CRSP's data release.
(2) Deflated Sharpe of the final candidate's IS result over the Phase 2 candidate
    ledger (3 candidates: sector+earnings, PCA k=15, PCA+earnings). Diagnostics
    were excluded from the count per the pre-registration.

Run:  python scripts/phase2_endgame.py
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
from src.signals.reversal import reversal_signal, winsorize

COSTS = (2, 5, 7)
# Phase 2 candidate net@7 Sharpes on the common-dates basis (research_log ledger).
PHASE2_TRIAL_SHARPES = [0.16, 0.26, 0.28]


def report(name, res):
    g, turn = res["gross"], res["turnover"]
    be = 1e4 * g.mean() / turn.mean()
    net7 = g - turn * (7 / 1e4)
    nets = "  ".join(f"net@{c} {metrics.sharpe_ratio(g - turn * (c / 1e4)):5.2f}" for c in COSTS)
    print(f"  {name:34s} gross {metrics.sharpe_ratio(g):5.2f} | ann {metrics.annualized_return(g) * 100:5.1f}%"
          f" | breakeven {be:5.1f} bps | {nets} | maxDD@7 {metrics.max_drawdown(net7) * 100:5.1f}%")


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    wcfg, ecfg, rcfg, pcfg = (cfg["signals"]["winsorize"], cfg["signals"]["earnings"],
                              cfg["signals"]["reversal"], cfg["portfolio"])

    resid, _ = pca_residuals(winsorize(returns, wcfg["lower"], wcfg["upper"]), eligible,
                             window=252, n_factors=15, reestimate=21)
    rdq = pd.read_parquet(ROOT / cfg["data"]["earnings_path"])
    links = pd.read_parquet(ROOT / cfg["data"]["ccm_link_path"])
    flag = earnings_in_window(
        earnings_event_panel(map_announcements_to_permnos(rdq, links), returns.index, returns.columns),
        window=ecfg["window"], extend=ecfg["extend"],
    )
    sig = engine.ewma_smooth(
        reversal_signal(resid, lookback=rcfg["lookback"], skip=rcfg["skip"], winsor=None),
        pcfg["smoothing_halflife"],
    )
    w = engine.signal_to_weights(
        sig, eligible=eligible & ~flag, gross_leverage=pcfg["gross_leverage"],
        max_weight=pcfg["max_weight"], market_neutral=pcfg["market_neutral"],
    )
    res = engine.run_backtest(w, returns, cost_bps=0.0)

    first_valid = resid.notna().any(axis=1).idxmax()
    print("=== Phase 2 endgame: FINAL candidate (PCA k=15 + earnings exclusion) ===")
    report(f"IS {first_valid.year}-{oos.year - 1} (development)",
           res[(res.index >= first_valid) & (res.index < oos)])
    report("2019-2024 [SPENT holdout - sanity only]", res[res.index >= oos])

    is_net7 = (res["gross"] - res["turnover"] * (7 / 1e4))[(res.index >= first_valid) & (res.index < oos)]
    dsr = metrics.deflated_sharpe_ratio(is_net7, n_trials=len(PHASE2_TRIAL_SHARPES),
                                        trial_sharpes=PHASE2_TRIAL_SHARPES)
    print(f"\nPhase 2 deflated Sharpe (IS net@7, {len(PHASE2_TRIAL_SHARPES)} candidates):"
          f" P(true Sharpe>0 after selection) = {dsr:.2f}")
    print("NOTE: the 2019-2024 figures are from a SPENT holdout (unsealed in Phase 1); the honest"
          "\nfinal exam awaits the 2025+ CRSP vintage.")


if __name__ == "__main__":
    main()
