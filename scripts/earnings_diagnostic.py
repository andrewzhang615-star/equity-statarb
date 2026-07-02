"""Phase 2, Layer B, Step 1 (diagnostic): is reversal weaker on earnings-window moves?

Pre-registered hypothesis (research_log.md): a signal formed from a move containing
an earnings announcement is information-driven and tends to drift (PEAD), so its
reversal should be weaker than on "clean" moves. If earnings-window reversal is NOT
materially weaker, the layer stops here.

Method (IN-SAMPLE 2000-2018 only):
  1. Sector-residual 5d reversal signal (Phase 1 signal, pre-smoothing).
  2. Flag = an rdq (mapped point-in-time gvkey->permno) in the trailing 5d window.
  3. Report: coverage by year (flagged share of eligible name-days; matched
     announcements), then IC (1d, 5d) and gross/breakeven for flagged vs clean.

Requires the earnings pull first:
  python -c "from src.data.earnings import pull_earnings_dates; pull_earnings_dates()"
Run:  python scripts/earnings_diagnostic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import numpy as np
import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG, ROOT
from src.data.earnings import earnings_event_panel, earnings_in_window, map_announcements_to_permnos
from src.data.load import load_eligible, load_returns_full, load_sector
from src.signals.residual import sector_residuals
from src.signals.reversal import reversal_signal, winsorize


def _row_corr(a: pd.DataFrame, b: pd.DataFrame) -> pd.Series:
    """Per-day Pearson correlation across columns, NaN-aware."""
    common = a.notna() & b.notna()
    a, b = a.where(common), b.where(common)
    a = a.sub(a.mean(axis=1), axis=0)
    b = b.sub(b.mean(axis=1), axis=0)
    num = (a * b).sum(axis=1)
    den = np.sqrt((a ** 2).sum(axis=1) * (b ** 2).sum(axis=1))
    return num / den.replace(0.0, np.nan)


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    is_mask = returns.index < oos

    # signal (Phase 1, pre-smoothing)
    rcfg, wcfg, ecfg = cfg["signals"]["reversal"], cfg["signals"]["winsorize"], cfg["signals"]["earnings"]
    resid = sector_residuals(
        winsorize(returns, wcfg["lower"], wcfg["upper"]), sector, eligible,
        min_peers=cfg["residual"]["sector_min_peers"],
    )
    sig = reversal_signal(resid, lookback=rcfg["lookback"], skip=rcfg["skip"], winsor=None)

    # earnings flag panel (point-in-time links; PAST announcements only)
    rdq = pd.read_parquet(ROOT / cfg["data"]["earnings_path"])
    links = pd.read_parquet(ROOT / cfg["data"]["ccm_link_path"])
    events = map_announcements_to_permnos(rdq, links)
    ev_panel = earnings_event_panel(events, returns.index, returns.columns)
    flag = earnings_in_window(ev_panel, window=ecfg["window"], extend=ecfg["extend"])

    valid = eligible & sig.notna()
    groups = {"earnings-in-window": valid & flag, "clean": valid & ~flag}

    print(f"=== Layer B diagnostic: reversal on earnings-window vs clean moves | IS 2000-{oos.year - 1} ===")
    print(f"matched announcements mapped to panel: {int(ev_panel.values.sum()):,}")

    print("\n(0) coverage by year (share of eligible name-days flagged | events landed)")
    fl_share = (groups["earnings-in-window"].sum(axis=1) / valid.sum(axis=1).replace(0, np.nan))[is_mask]
    ev_year = ev_panel[is_mask].sum(axis=1).groupby(ev_panel.index[is_mask].year).sum()
    for y, share in fl_share.groupby(fl_share.index.year).mean().items():
        print(f"  {y}: {share * 100:5.1f}%  | {int(ev_year.get(y, 0)):6,} events")

    print("\n(1) rank-IC of reversal signal vs forward residual returns")
    print("  group                 IC(1d)   t      IC(5d)   t     names/day")
    for name, m in groups.items():
        row = [name]
        for h in (1, 5):
            fwd = resid.rolling(h).sum().shift(-h)
            ic = _row_corr(sig.where(m)[is_mask].rank(axis=1), fwd.where(m)[is_mask].rank(axis=1)).dropna()
            row += [ic.mean(), ic.mean() / ic.std(ddof=1) * np.sqrt(len(ic))]
        n_day = int(m[is_mask].sum(axis=1).mean())
        print(f"  {row[0]:20s}  {row[1]:+.4f} {row[2]:6.1f}   {row[3]:+.4f} {row[4]:6.1f}   {n_day:6d}")

    print("\n(2) gross backtests (reversal traded within each group)")
    print("  group                 gross Sh   ann%   turnover   breakeven")
    pcfg = cfg["portfolio"]
    for name, m in groups.items():
        w = engine.signal_to_weights(
            sig, eligible=m, gross_leverage=pcfg["gross_leverage"],
            max_weight=pcfg["max_weight"], market_neutral=pcfg["market_neutral"],
        )
        res = engine.run_backtest(w, returns, cost_bps=0.0)[is_mask]
        g, turn = res["gross"], res["turnover"]
        be = 1e4 * g.mean() / turn.mean()
        print(f"  {name:20s}   {metrics.sharpe_ratio(g):6.2f}  {metrics.annualized_return(g) * 100:6.1f}"
              f"   {turn.mean():7.3f}    {be:6.1f} bps")

    print("\n(hypothesis: earnings-in-window reversal is materially weaker than clean)")


if __name__ == "__main__":
    main()
