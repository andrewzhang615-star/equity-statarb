"""Diagnostics on the locked candidate (IN-SAMPLE 2000-2018 only; no tuning).

(1) Signal IC decay: rank-IC of the (pre-smoothing) sector-residual reversal signal
    vs forward RESIDUAL returns at 1/2/3/5/10 days -- shows the predictive horizon
    and whether 5-day lookback + EWMA make sense.
(2) Macro / regime conditioning: strategy performance by market realized-volatility
    regime, cross-sectional dispersion regime, and up/down market days -- tests the
    "reversal is stronger in high-vol / dislocated markets" mechanism.

Mirrors candidate_weights() (sector residual -> reversal -> EWMA hl=5) but keeps the
intermediate residual so we can measure IC. Holdout sealed. Run from repo root.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import numpy as np
import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG
from src.data.load import load_eligible, load_returns_full, load_sector
from src.signals.residual import sector_residuals
from src.signals.reversal import reversal_signal, winsorize


def _row_corr(a: pd.DataFrame, b: pd.DataFrame) -> pd.Series:
    """Per-row (per-day) Pearson correlation over columns, NaN-aware."""
    common = a.notna() & b.notna()
    a, b = a.where(common), b.where(common)
    a = a.sub(a.mean(axis=1), axis=0)
    b = b.sub(b.mean(axis=1), axis=0)
    num = (a * b).sum(axis=1)
    den = np.sqrt((a ** 2).sum(axis=1) * (b ** 2).sum(axis=1))
    return num / den.replace(0.0, np.nan)


def _stat(returns) -> str:
    return f"ann {metrics.annualized_return(returns) * 100:6.1f}%  sharpe {metrics.sharpe_ratio(returns):5.2f}"


def main() -> None:
    cfg = CONFIG
    returns = load_returns_full().astype("float32")
    eligible = load_eligible().reindex_like(returns).fillna(False)
    sector = load_sector().reindex_like(returns)
    rcfg, wcfg, pcfg = cfg["signals"]["reversal"], cfg["signals"]["winsorize"], cfg["portfolio"]
    oos = pd.Timestamp(cfg["evaluation"]["oos_start"])
    is_mask = returns.index < oos

    # --- shared: residual panel + signal (mirrors candidate_weights) ---
    resid = sector_residuals(winsorize(returns, wcfg["lower"], wcfg["upper"]), sector, eligible,
                             min_peers=cfg["residual"]["sector_min_peers"])
    sig = reversal_signal(resid, lookback=rcfg["lookback"], skip=rcfg["skip"], winsor=None)

    # ---------------- (1) IC decay ----------------
    print("=== (1) Signal IC decay (rank-IC vs forward residual returns, IS) ===")
    print("  horizon(d)   mean rank-IC   IC t-stat")
    sig_is = sig.where(eligible)[is_mask]
    for h in (1, 2, 3, 5, 10):
        fwd = resid.rolling(h).sum().shift(-h).where(eligible)[is_mask]
        ic = _row_corr(sig_is.rank(axis=1), fwd.rank(axis=1)).dropna()
        tstat = ic.mean() / ic.std(ddof=1) * np.sqrt(len(ic))
        print(f"     {h:3d}        {ic.mean():+.4f}        {tstat:6.1f}")

    # ---------------- (2) Macro / regime conditioning ----------------
    sig_sm = engine.ewma_smooth(sig, pcfg["smoothing_halflife"])
    w = engine.signal_to_weights(sig_sm, eligible=eligible, gross_leverage=pcfg["gross_leverage"],
                                 max_weight=pcfg["max_weight"], market_neutral=pcfg["market_neutral"])
    cost_bps = cfg["costs"]["commission_bps"] + cfg["costs"]["slippage_bps"]
    res = engine.run_backtest(w, returns, cost_bps=cost_bps)
    gross = res["gross"][is_mask]

    mkt = returns.where(eligible).mean(axis=1)
    mkt_vol = mkt.rolling(21).std().shift(1)[is_mask]          # lagged vol regime
    dispersion = returns.where(eligible).std(axis=1).shift(1)[is_mask]  # lagged x-sec dispersion
    up_day = (mkt[is_mask] > 0)

    print("\n=== (2) Macro / regime conditioning (GROSS, IS) ===")
    for name, regime in [("market realized vol (21d)", mkt_vol), ("cross-sectional dispersion", dispersion)]:
        bucket = pd.qcut(regime, 3, labels=["low", "mid", "high"])
        print(f"  by {name}:")
        for b in ["low", "mid", "high"]:
            print(f"     {b:4s}: {_stat(gross[bucket == b])}")
    print("  by market direction:")
    print(f"     up-days  : {_stat(gross[up_day])}")
    print(f"     down-days: {_stat(gross[~up_day])}")
    print("\n  (hypothesis: reversal is stronger in high-vol / high-dispersion regimes.)")


if __name__ == "__main__":
    main()
