"""Build the backtest panels from the raw CRSP pull.

The central correctness rule of this project lives here:

    `returns_full`  = the PnL panel. It is NEVER masked by price, liquidity, or
                      eligibility. Delisting returns are folded in (and imputed
                      when missing) so a held loser cannot "disappear."

    `eligible`      = a boolean tradability mask (price >= min_price AND top-N by
                      average dollar volume, AND not the delisting row). It is used
                      ONLY to decide which names may receive new target weights —
                      never to erase realized returns of names already held.

Filters decide what we are allowed to trade; they do not edit history.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import CONFIG, ROOT


def _check_unique_permno_date(daily: pd.DataFrame) -> None:
    """Guard against an overlapping dsenames join silently averaging returns.

    pivot_table() would quietly mean-collapse duplicate (permno, date) rows, so we
    fail loudly instead. If this ever fires on a real pull, dedup the dsenames
    join (e.g. keep the row with the latest nameendt) before building panels.
    """
    dup = daily.duplicated(["permno", "date"]).sum()
    if dup:
        example = daily[daily.duplicated(["permno", "date"], keep=False)].head(4)
        raise ValueError(
            f"{dup} duplicate (permno, date) rows before pivot — likely an overlapping "
            f"dsenames join. Dedup (e.g. keep latest nameendt) before building panels.\n{example}"
        )


# --------------------------------------------------------------------------- #
# Delisting returns
# --------------------------------------------------------------------------- #
def _in_ranges(codes: pd.Series, ranges) -> pd.Series:
    """Boolean: is each code within any [lo, hi] range (inclusive)?"""
    out = pd.Series(False, index=codes.index)
    for lo, hi in ranges:
        out |= (codes >= lo) & (codes <= hi)
    return out


def impute_delisting_returns(delist: pd.DataFrame, dcfg: dict) -> pd.DataFrame:
    """Add an effective delisting return ``dl_eff`` with explicit imputation.

    - missing dlret + performance code  -> dcfg['missing_perf_dlret'] (e.g. -0.30)
    - missing dlret + non-performance   -> 0.0
    - present dlret                      -> use as-is
    - optional bankruptcy stress overrides dl_eff for configured codes.
    """
    d = delist.copy()
    codes = pd.to_numeric(d["dlstcd"], errors="coerce")
    dlret = pd.to_numeric(d["dlret"], errors="coerce")
    perf = _in_ranges(codes, dcfg["perf_code_ranges"])
    missing = dlret.isna()

    dl_eff = dlret.copy()
    dl_eff[missing & perf] = dcfg["missing_perf_dlret"]
    dl_eff[missing & ~perf] = 0.0

    stress = dcfg.get("bankruptcy_stress", {}) or {}
    if stress.get("enabled"):
        dl_eff[codes.isin(set(stress.get("codes", [])))] = stress["value"]

    d["dl_eff"] = dl_eff
    return d


def apply_delisting_returns(daily: pd.DataFrame, delist: pd.DataFrame, dcfg: dict) -> pd.DataFrame:
    """Fold delisting returns into ``ret_adj`` and flag the terminal row.

    Matched: compound dl_eff into the row on the delisting date.
    Unmatched (delisting date absent from the price file): compound dl_eff into the
    last available date ON OR BEFORE dlstdt, so the loss is never silently dropped.
    A ``delist_event`` flag marks every row where a delisting return was applied,
    so eligibility can exclude it.
    """
    daily = daily.copy()
    daily["ret_adj"] = pd.to_numeric(daily["ret"], errors="coerce")
    daily["delist_event"] = False

    # Only ACTUAL delistings: dlstcd >= 200 (100 = still trading) with a real date.
    # CRSP's dsedelist carries an "active" row per security; without this filter we
    # would flag live stocks as delisted and wrongly drop them from the universe.
    codes = pd.to_numeric(delist["dlstcd"], errors="coerce")
    delist = delist[(codes >= 200) & delist["dlstdt"].notna()]

    d = impute_delisting_returns(delist, dcfg)

    # --- matched delistings: compound onto the exact delisting-date row ---
    daily = daily.merge(
        d[["permno", "dlstdt", "dl_eff"]].rename(columns={"dlstdt": "date"}),
        on=["permno", "date"], how="left",
    )
    m = daily["dl_eff"].notna()
    daily.loc[m, "ret_adj"] = (1 + daily.loc[m, "ret"].fillna(0.0)) * (1 + daily.loc[m, "dl_eff"]) - 1
    daily.loc[m, "delist_event"] = True
    daily = daily.drop(columns="dl_eff")

    # --- unmatched delistings: attach to last available date ON OR BEFORE dlstdt ---
    daily_keys = pd.MultiIndex.from_arrays([daily["permno"], daily["date"]])
    event_keys = pd.MultiIndex.from_arrays([d["permno"], d["dlstdt"]])
    unmatched = d[~event_keys.isin(daily_keys)]
    if len(unmatched):
        ud = unmatched[["permno", "dlstdt", "dl_eff"]].drop_duplicates("permno")
        cand = daily[["permno", "date"]].merge(ud[["permno", "dlstdt"]], on="permno", how="inner")
        cand = cand[cand["date"] <= cand["dlstdt"]]
        last_on_before = cand.groupby("permno")["date"].max()
        attach = (
            ud.assign(date=ud["permno"].map(last_on_before))
            .dropna(subset=["date"])
            .rename(columns={"dl_eff": "dl_add"})
        )
        daily = daily.merge(attach[["permno", "date", "dl_add"]], on=["permno", "date"], how="left")
        a = daily["dl_add"].notna()
        daily.loc[a, "ret_adj"] = (1 + daily.loc[a, "ret_adj"].fillna(0.0)) * (1 + daily.loc[a, "dl_add"]) - 1
        daily.loc[a, "delist_event"] = True
        daily = daily.drop(columns="dl_add")

    return daily


# --------------------------------------------------------------------------- #
# Panels
# --------------------------------------------------------------------------- #
def build_returns_full(daily: pd.DataFrame) -> pd.DataFrame:
    """PnL panel (dates x permno) of total returns. No masking, ever."""
    return daily.pivot_table(index="date", columns="permno", values="ret_adj")


def build_eligibility(daily: pd.DataFrame, dcfg: dict) -> pd.DataFrame:
    """Boolean tradability mask: price >= min_price AND top-N by average $-volume,
    AND not a delisting row.

    Computed contemporaneously (uses each day's own price/volume, known at the
    decision-time close). The single sufficient look-ahead lag is applied by the
    backtest engine, which shifts weights one period before they earn returns —
    so we deliberately do NOT double-lag here. (Flagged for review.)
    """
    daily = daily.copy()
    daily["dollar_vol"] = daily["prc"].abs() * daily["vol"]
    prc = daily.pivot_table(index="date", columns="permno", values="prc")
    dvol = daily.pivot_table(index="date", columns="permno", values="dollar_vol")

    price_ok = prc.abs() >= dcfg["min_price"]
    adv = dvol.rolling(dcfg["adv_window"], min_periods=dcfg["adv_min_periods"]).mean()
    liquid_ok = adv.rank(axis=1, ascending=False) <= dcfg["universe_size"]
    eligible = (price_ok & liquid_ok).fillna(False)

    # Never let a signal try to trade a name on the day it delists.
    if "delist_event" in daily.columns:
        de = (
            daily.pivot_table(index="date", columns="permno", values="delist_event", aggfunc="max")
            .reindex(index=eligible.index, columns=eligible.columns)
            .fillna(0)
            .astype(bool)
        )
        eligible = eligible & ~de

    return eligible


def build_panel(config: dict | None = None):
    """Build and cache (returns_full, eligible) from the raw CRSP files."""
    cfg = config or CONFIG
    dcfg, delcfg = cfg["data"], cfg["delisting"]

    daily = pd.read_parquet(ROOT / dcfg["raw_path"])
    _check_unique_permno_date(daily)
    delist = pd.read_parquet(ROOT / dcfg["delist_path"])

    daily = apply_delisting_returns(daily, delist, delcfg)
    returns_full = build_returns_full(daily)
    eligible = build_eligibility(daily, dcfg).reindex(
        index=returns_full.index, columns=returns_full.columns
    ).fillna(False)

    rf_out = ROOT / dcfg["returns_full_path"]
    el_out = ROOT / dcfg["eligible_path"]
    rf_out.parent.mkdir(parents=True, exist_ok=True)
    el_out.parent.mkdir(parents=True, exist_ok=True)
    returns_full.to_parquet(rf_out)
    eligible.to_parquet(el_out)
    print(f"returns_full: {returns_full.shape[0]:,} days x {returns_full.shape[1]:,} names")
    print(f"eligible:     {int(eligible.sum(axis=1).mean()):,} names tradable on an average day")
    return returns_full, eligible


def load_returns_full(config: dict | None = None) -> pd.DataFrame:
    cfg = config or CONFIG
    path = ROOT / cfg["data"]["returns_full_path"]
    return pd.read_parquet(path) if path.exists() else build_panel(config)[0]


def load_eligible(config: dict | None = None) -> pd.DataFrame:
    cfg = config or CONFIG
    path = ROOT / cfg["data"]["eligible_path"]
    return pd.read_parquet(path) if path.exists() else build_panel(config)[1]


if __name__ == "__main__":
    build_panel()
