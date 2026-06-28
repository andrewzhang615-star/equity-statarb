"""Pull RAW CRSP daily data via the WRDS Python package.

Design rule: **the pull is dumb and complete.** It fetches raw fields only — no
delisting imputation, no return combining, no universe masking. Every judgment
call (imputing missing delisting returns, building the tradable universe,
look-ahead lags) happens downstream in ``load.build_panel`` from ``config.yaml``,
where it is visible, swappable, and testable. That also means the sensitivity
analysis over imputation conventions never requires a re-pull.

Requires a WRDS account. The first ``wrds.Connection()`` call prompts for your
credentials and offers to store a ``~/.pgpass`` so later pulls are passwordless.

Why CRSP: survivorship-bias-free, with *delisting returns* and point-in-time
share/exchange/SIC codes.
"""
from __future__ import annotations

import pandas as pd

from src.config import CONFIG, ROOT


def pull_crsp_daily(username: str | None = None, config: dict | None = None) -> None:
    """Download raw CRSP daily prices/returns + delisting events and cache them.

    Writes two parquet files (raw, uncombined):
      - data/raw/crsp_daily.parquet   (dsf joined to point-in-time dsenames)
      - data/raw/crsp_delist.parquet  (dsedelist: dlstdt, dlret, dlstcd)
    """
    import wrds  # imported lazily so the rest of the repo runs without credentials

    cfg = (config or CONFIG)["data"]
    start, end = cfg["start_date"], cfg["end_date"]
    shrcd = tuple(cfg["share_codes"])
    exchcd = tuple(cfg["exchange_codes"])

    db = wrds.Connection(wrds_username=username) if username else wrds.Connection()
    try:
        # Daily stock file joined to the names table for POINT-IN-TIME filters.
        # Note b.siccd (as-of SIC), NOT header SIC, to avoid look-ahead on sector.
        daily = db.raw_sql(
            f"""
            SELECT a.permno, a.permco, a.date, a.ret, a.prc, a.vol, a.shrout,
                   a.askhi, a.bidlo,
                   b.shrcd, b.exchcd, b.siccd, b.ticker
            FROM crsp.dsf AS a
            LEFT JOIN crsp.dsenames AS b
              ON a.permno = b.permno
             AND b.namedt <= a.date
             AND a.date <= b.nameendt
            WHERE a.date BETWEEN '{start}' AND '{end}'
              AND b.shrcd IN {shrcd}
              AND b.exchcd IN {exchcd}
            """,
            date_cols=["date"],
        )

        # Delisting events, raw — dlret/dlstcd kept as-is (NaN preserved).
        delist = db.raw_sql(
            f"""
            SELECT permno, dlstdt, dlret, dlstcd
            FROM crsp.dsedelist
            WHERE dlstdt BETWEEN '{start}' AND '{end}'
            """,
            date_cols=["dlstdt"],
        )
    finally:
        db.close()

    raw_out = ROOT / cfg["raw_path"]
    del_out = ROOT / cfg["delist_path"]
    raw_out.parent.mkdir(parents=True, exist_ok=True)
    del_out.parent.mkdir(parents=True, exist_ok=True)
    daily.to_parquet(raw_out)
    delist.to_parquet(del_out)
    print(f"Saved {len(daily):,} daily rows -> {raw_out}")
    print(f"Saved {len(delist):,} delisting rows -> {del_out}")


if __name__ == "__main__":
    pull_crsp_daily()
