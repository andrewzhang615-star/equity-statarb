"""Phase 2, Layer B, Step 2: the earnings-exclusion CANDIDATE strategy (IS only).

Pre-registered after the Step 1 gate passed: baseline candidate weights, but names
with an earnings announcement in the trailing 5d signal window are ineligible for
weight (forced to zero while flagged; signal computation unchanged). Compared
against the unconditional baseline on identical IS data.

This is a candidate configuration -> counts in the Phase 2 DSR trial ledger.

Run:  python scripts/earnings_exclusion.py
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
from src.portfolio.construct import candidate_weights

COSTS = (2, 5, 7)


def report(name: str, w: pd.DataFrame, returns: pd.DataFrame, is_mask) -> None:
    res = engine.run_backtest(w, returns, cost_bps=0.0)[is_mask]
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
    is_mask = returns.index < oos
    ecfg = cfg["signals"]["earnings"]

    rdq = pd.read_parquet(ROOT / cfg["data"]["earnings_path"])
    links = pd.read_parquet(ROOT / cfg["data"]["ccm_link_path"])
    events = map_announcements_to_permnos(rdq, links)
    flag = earnings_in_window(
        earnings_event_panel(events, returns.index, returns.columns),
        window=ecfg["window"], extend=ecfg["extend"],
    )

    print(f"=== Layer B step 2: earnings exclusion vs baseline | IS 2000-{oos.year - 1} ===")
    w_base = candidate_weights(returns, eligible, sector, cfg)
    report("baseline candidate", w_base, returns, is_mask)
    w_excl = candidate_weights(returns, eligible, sector, cfg, weight_eligible=eligible & ~flag)
    report("earnings-excluded", w_excl, returns, is_mask)


if __name__ == "__main__":
    main()
