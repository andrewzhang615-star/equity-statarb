"""Tests for the Layer B earnings-event machinery (point-in-time links, timing)."""
import pandas as pd

from src.data.earnings import (
    earnings_event_panel,
    earnings_in_window,
    map_announcements_to_permnos,
)


def _bdays(start, n):
    return pd.date_range(start, periods=n, freq="B")


def test_link_must_be_active_on_announcement_date():
    rdq = pd.DataFrame({"gvkey": ["001", "001"],
                        "rdq": pd.to_datetime(["2005-05-02", "2015-05-04"])})
    links = pd.DataFrame({
        "gvkey": ["001", "001"],
        "permno": [111, 222],  # company remapped to a new permno in 2010
        "linkdt": pd.to_datetime(["2000-01-01", "2010-01-01"]),
        "linkenddt": [pd.Timestamp("2009-12-31"), pd.NaT],  # NaT = still active
        "linktype": ["LU", "LU"], "linkprim": ["P", "P"],
    })
    out = map_announcements_to_permnos(rdq, links)
    got = set(map(tuple, out[["permno"]].assign(y=out["rdq"].dt.year).values))
    assert got == {(111, 2005), (222, 2015)}  # each rdq maps via the link ACTIVE then


def test_weekend_announcement_hits_next_trading_day():
    idx = _bdays("2020-01-06", 10)  # Mon..; 2020-01-11 is a Saturday
    events = pd.DataFrame({"permno": [7], "rdq": [pd.Timestamp("2020-01-11")]})
    panel = earnings_event_panel(events, idx, [7])
    assert panel.loc[pd.Timestamp("2020-01-13"), 7]        # Monday after
    assert panel.sum().sum() == 1


def test_in_window_flags_trailing_days_only():
    idx = _bdays("2020-01-06", 15)
    panel = pd.DataFrame(False, index=idx, columns=[1])
    panel.iloc[5, 0] = True  # event on day 5
    flag = earnings_in_window(panel, window=5, extend=0)
    assert not flag.iloc[4, 0]                 # day BEFORE the event: never flagged
    assert flag.iloc[5, 0] and flag.iloc[9, 0]  # event day .. event+4 flagged
    assert not flag.iloc[10, 0]                # window over

    ext = earnings_in_window(panel, window=5, extend=1)
    assert ext.iloc[10, 0] and not ext.iloc[11, 0]  # rdq+1 smear extends one day
