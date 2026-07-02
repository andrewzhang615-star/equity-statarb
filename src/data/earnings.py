"""Earnings-announcement dates (Phase 2, Layer B).

`pull_earnings_dates` downloads Compustat quarterly report dates (``comp.fundq.rdq``)
and the CRSP/Compustat link history (``crsp.ccmxpf_lnkhist``), saved raw.

`map_announcements_to_permnos` maps gvkey announcements to permnos using ONLY
links active on the announcement date (point-in-time: a link valid today must not
be projected backward onto old announcements).

`earnings_event_panel` places each announcement on its trading day (first trading
day ON OR AFTER rdq, so weekend/holiday announcements hit the next session).

`earnings_in_window` builds the boolean flag panel: True at (t, i) if name i had
an announcement within the trailing `window` trading days ending at t. Only PAST
events are used -- there is no pre-announcement blackout (that would need an
ex-ante calendar). `extend=1` first smears each event to the next trading day
(pre-registered robustness for after-close announcements).
"""
from __future__ import annotations

import pandas as pd

from src.config import CONFIG, ROOT

FAR_FUTURE = pd.Timestamp("2099-12-31")


def pull_earnings_dates(username: str | None = None, config: dict | None = None) -> None:
    """Download raw rdq + link tables from WRDS and cache them (raw, unjoined)."""
    import wrds  # lazy: rest of the module works without credentials

    cfg = (config or CONFIG)["data"]
    start, end = cfg["start_date"], cfg["end_date"]
    db = wrds.Connection(wrds_username=username) if username else wrds.Connection()
    try:
        rdq = db.raw_sql(
            f"""
            SELECT gvkey, datadate, rdq
            FROM comp.fundq
            WHERE rdq IS NOT NULL AND rdq BETWEEN '{start}' AND '{end}'
            """,
            date_cols=["datadate", "rdq"],
        )
        links = db.raw_sql(
            """
            SELECT gvkey, lpermno AS permno, linkdt, linkenddt, linktype, linkprim
            FROM crsp.ccmxpf_lnkhist
            WHERE linktype IN ('LU','LC') AND linkprim IN ('P','C')
            """,
            date_cols=["linkdt", "linkenddt"],
        )
    finally:
        db.close()

    rdq_out = ROOT / cfg["earnings_path"]
    link_out = ROOT / cfg["ccm_link_path"]
    rdq_out.parent.mkdir(parents=True, exist_ok=True)
    rdq.to_parquet(rdq_out)
    links.to_parquet(link_out)
    print(f"Saved {len(rdq):,} rdq rows -> {rdq_out}")
    print(f"Saved {len(links):,} link rows -> {link_out}")


def map_announcements_to_permnos(rdq: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """(gvkey, rdq) -> unique (permno, rdq), keeping only links active ON the rdq date."""
    l = links.copy()
    l["linkenddt"] = l["linkenddt"].fillna(FAR_FUTURE)  # open-ended link = still active
    m = rdq.merge(l[["gvkey", "permno", "linkdt", "linkenddt"]], on="gvkey", how="inner")
    m = m[(m["linkdt"] <= m["rdq"]) & (m["rdq"] <= m["linkenddt"])]
    return m[["permno", "rdq"]].drop_duplicates()


def earnings_event_panel(
    events: pd.DataFrame, index: pd.DatetimeIndex, columns
) -> pd.DataFrame:
    """Boolean (dates x permno) panel, True on the first trading day >= rdq."""
    idx = pd.DatetimeIndex(index)
    pos = idx.searchsorted(pd.DatetimeIndex(events["rdq"]).values)
    ok = pos < len(idx)  # announcements after the last trading day are dropped
    ev = pd.DataFrame({"date": idx[pos[ok]], "permno": events["permno"].to_numpy()[ok]})
    panel = pd.DataFrame(False, index=idx, columns=columns)
    ev = ev[ev["permno"].isin(panel.columns)].drop_duplicates()
    panel.values[idx.get_indexer(ev["date"]), panel.columns.get_indexer(ev["permno"])] = True
    return panel


def earnings_in_window(event_panel: pd.DataFrame, window: int = 5, extend: int = 0) -> pd.DataFrame:
    """True at (t, i) if an event occurred in the trailing `window` days ending at t.

    `extend` first carries each event forward `extend` extra trading days
    (after-close robustness), so the flag covers [event .. event + extend + window - 1].
    """
    p = event_panel.astype("float32")
    if extend:
        p = p.rolling(extend + 1, min_periods=1).max()
    return p.rolling(window, min_periods=1).max().astype(bool)
