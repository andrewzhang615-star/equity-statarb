"""Phase 2, Layer A, Step 1 (diagnostic): is reversal stronger after LOW-volume moves?

Pre-registered hypothesis (research_log.md): a residual price move on abnormally
low volume is more likely a temporary liquidity dislocation (reverts); a move on
high volume is more likely informed (does not revert). If the low-AV tercile shows
no edge advantage, the layer STOPS here -- that is a recorded result, not a
failure.

Method (IN-SAMPLE 2000-2018 only; no strategy variant is built here):
  1. Sector-residual 5d reversal signal (Phase 1 signal, pre-smoothing).
  2. Abnormal volume AV = 5d signal-window mean dollar volume / trailing 60d base
     (non-overlapping). Cross-sectional AV terciles each day among valid names.
  3. Report by tercile: rank-IC vs forward residual returns (1d, 5d) and a gross
     tercile backtest (gross Sharpe, turnover, breakeven).

Run:  python scripts/volume_diagnostic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on sys.path

import numpy as np
import pandas as pd

from src.backtest import engine, metrics
from src.config import CONFIG
from src.data.load import dollar_volume_panel, load_eligible, load_returns_full, load_sector
from src.signals.residual import sector_residuals
from src.signals.reversal import reversal_signal, winsorize
from src.signals.volume import abnormal_volume


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

    rcfg, wcfg, vcfg = cfg["signals"]["reversal"], cfg["signals"]["winsorize"], cfg["signals"]["volume"]
    resid = sector_residuals(
        winsorize(returns, wcfg["lower"], wcfg["upper"]), sector, eligible,
        min_peers=cfg["residual"]["sector_min_peers"],
    )
    sig = reversal_signal(resid, lookback=rcfg["lookback"], skip=rcfg["skip"], winsor=None)

    dv = dollar_volume_panel(cfg).reindex_like(returns)
    av = abnormal_volume(dv, vcfg["window"], vcfg["base_window"], vcfg["min_base"])

    valid = eligible & sig.notna() & av.notna()
    av_pct = av.where(valid).rank(axis=1, pct=True)
    terciles = {
        "low AV": av_pct <= 1 / 3,
        "mid AV": (av_pct > 1 / 3) & (av_pct <= 2 / 3),
        "high AV": av_pct > 2 / 3,
    }

    print(f"=== Layer A diagnostic: reversal by abnormal-volume tercile | IS 2000-{oos.year - 1} ===")
    print(f"avg valid names/day: {int(valid[is_mask].sum(axis=1).mean())}")

    print("\n(1) rank-IC of reversal signal vs forward residual returns, by AV tercile")
    print("  tercile     IC(1d)   t      IC(5d)   t")
    for name, m in terciles.items():
        row = [name]
        for h in (1, 5):
            fwd = resid.rolling(h).sum().shift(-h)
            ic = _row_corr(sig.where(m)[is_mask].rank(axis=1), fwd.where(m)[is_mask].rank(axis=1)).dropna()
            row += [ic.mean(), ic.mean() / ic.std(ddof=1) * np.sqrt(len(ic))]
        print(f"  {row[0]:8s}  {row[1]:+.4f} {row[2]:6.1f}   {row[3]:+.4f} {row[4]:6.1f}")

    print("\n(2) gross tercile backtests (reversal traded within each tercile)")
    print("  tercile     gross Sh   ann%   turnover   breakeven")
    pcfg = cfg["portfolio"]
    for name, m in terciles.items():
        w = engine.signal_to_weights(
            sig, eligible=m, gross_leverage=pcfg["gross_leverage"],
            max_weight=pcfg["max_weight"], market_neutral=pcfg["market_neutral"],
        )
        res = engine.run_backtest(w, returns, cost_bps=0.0)[is_mask]
        g, turn = res["gross"], res["turnover"]
        be = 1e4 * g.mean() / turn.mean()
        print(f"  {name:8s}   {metrics.sharpe_ratio(g):6.2f}  {metrics.annualized_return(g) * 100:6.1f}"
              f"   {turn.mean():7.3f}    {be:6.1f} bps")

    print("\n(hypothesis: low-AV tercile shows higher IC and higher breakeven than high-AV)")


if __name__ == "__main__":
    main()
