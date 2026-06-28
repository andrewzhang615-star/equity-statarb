"""Tests for the data-hygiene foundation.

The point of these tests: prove that a held loser's loss (including delistings)
CANNOT silently vanish from PnL, and that imputation is applied correctly.
"""
import numpy as np
import pandas as pd

from src.backtest import engine
from src.data import load

DCFG = {
    "missing_perf_dlret": -0.30,
    "perf_code_ranges": [[500, 500], [520, 584]],
    "bankruptcy_stress": {"enabled": False},
}


def test_imputation_only_for_missing_performance_codes():
    delist = pd.DataFrame(
        {
            "permno": [1, 2, 3, 4],
            "dlstdt": pd.to_datetime(["2020-01-10"] * 4),
            "dlret": [np.nan, np.nan, -0.6, np.nan],
            "dlstcd": [574, 241, 500, 520],  # perf, merger, perf(w/ ret), perf
        }
    )
    out = load.impute_delisting_returns(delist, DCFG).set_index("permno")["dl_eff"]
    assert out[1] == -0.30   # missing performance -> imputed
    assert out[2] == 0.0     # missing merger -> 0, NOT imputed
    assert out[3] == -0.6    # present return -> untouched
    assert out[4] == -0.30   # missing performance -> imputed


def test_delisting_loss_attaches_when_date_matches():
    daily = pd.DataFrame(
        {
            "permno": [1, 1, 1],
            "date": pd.to_datetime(["2020-01-08", "2020-01-09", "2020-01-10"]),
            "ret": [0.01, -0.02, 0.0],
            "prc": [10.0, 10.0, 10.0],
            "vol": [100, 100, 100],
        }
    )
    delist = pd.DataFrame({"permno": [1], "dlstdt": pd.to_datetime(["2020-01-10"]),
                           "dlret": [np.nan], "dlstcd": [574]})
    out = load.apply_delisting_returns(daily, delist, DCFG)
    last = out.loc[out["date"] == "2020-01-10", "ret_adj"].iloc[0]
    assert abs(last - (-0.30)) < 1e-12   # (1+0)*(1-0.30)-1


def test_delisting_loss_attaches_when_date_missing():
    # Delisting date 01-12 has NO matching price row -> attach to last date (01-09).
    daily = pd.DataFrame(
        {
            "permno": [5, 5],
            "date": pd.to_datetime(["2020-01-08", "2020-01-09"]),
            "ret": [0.0, 0.0],
            "prc": [10.0, 10.0],
            "vol": [100, 100],
        }
    )
    delist = pd.DataFrame({"permno": [5], "dlstdt": pd.to_datetime(["2020-01-12"]),
                           "dlret": [np.nan], "dlstcd": [574]})
    out = load.apply_delisting_returns(daily, delist, DCFG)
    last = out.loc[out["date"] == "2020-01-09", "ret_adj"].iloc[0]
    assert abs(last - (-0.30)) < 1e-12   # loss not dropped despite missing row


def test_held_delisting_loser_does_not_disappear_from_pnl():
    dates = pd.to_datetime(["2020-01-06", "2020-01-07", "2020-01-08", "2020-01-09"])
    # C delists at d1 with a -40% return, then is gone.
    returns_full = pd.DataFrame(
        {"A": [0.0, 0.0, 0.0, 0.0], "C": [0.0, -0.40, np.nan, np.nan]}, index=dates
    )
    # Hold C long / A short through d1, then exit both at d2.
    weights = pd.DataFrame(
        {"A": [-1.0, -1.0, 0.0, 0.0], "C": [1.0, 1.0, 0.0, 0.0]}, index=dates
    )
    res = engine.run_backtest(weights, returns_full)
    # The -40% loss is realized on d1 (w_d0 applied to r_d1), not skipped:
    assert abs(res["gross"].iloc[1] - (-0.40)) < 1e-12
    # Exiting the position registers turnover (it is not a free teleport to flat):
    assert res["turnover"].iloc[2] > 0


def test_eligibility_excludes_low_price_and_illiquid():
    dates = pd.to_datetime(["2020-01-06", "2020-01-07", "2020-01-08"])
    daily = pd.DataFrame(
        {
            "permno": [10, 10, 10, 20, 20, 20, 30, 30, 30],
            "date": list(dates) * 3,
            "prc": [2.0, 2.0, 2.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],  # 10 is sub-$5
            "vol": [1000, 1000, 1000, 500, 500, 500, 400, 400, 400],
        }
    )
    dcfg = {"min_price": 5.0, "universe_size": 2, "adv_window": 2, "adv_min_periods": 1}
    elig = load.build_eligibility(daily, dcfg)
    assert elig[10].sum() == 0      # excluded on price regardless of volume
    assert elig[20].any()           # liquid + priced -> tradable


def test_eligibility_uses_prior_close():
    # A name that was a sub-$5 penny stock yesterday must not be tradable today just
    # because it spiked over $5 today (reversal would otherwise short the spike).
    dates = pd.to_datetime(["2020-01-06", "2020-01-07", "2020-01-08"])
    daily = pd.DataFrame(
        {
            "permno": [50, 50, 50, 60, 60, 60],
            "date": list(dates) * 2,
            "prc": [3.0, 3.0, 10.0, 10.0, 10.0, 10.0],  # 50 spikes today; 60 always priced
            "vol": [1000, 1000, 1000, 1000, 1000, 1000],
        }
    )
    dcfg = {"min_price": 5.0, "universe_size": 5, "adv_window": 2, "adv_min_periods": 1}
    elig = load.build_eligibility(daily, dcfg)
    assert elig[50].sum() == 0   # same-day spike to $10 doesn't qualify (prior close $3)
    assert elig[60].iloc[2]      # tradable via prior close >= $5


def test_delisting_row_is_not_eligible():
    dates = pd.to_datetime(["2020-01-06", "2020-01-07", "2020-01-08"])
    daily = pd.DataFrame(
        {
            "permno": [40, 40, 40],
            "date": list(dates),
            "prc": [10.0, 10.0, 10.0],          # liquid + priced the whole time
            "vol": [1000, 1000, 1000],
            "delist_event": [False, False, True],  # delists on the last day
        }
    )
    dcfg = {"min_price": 5.0, "universe_size": 5, "adv_window": 2, "adv_min_periods": 1}
    elig = load.build_eligibility(daily, dcfg)
    assert elig[40].iloc[1]          # tradable before delisting (has a prior close)
    assert not elig[40].iloc[2]      # NOT tradable on the delisting row


def test_active_code_is_not_treated_as_delisting():
    dates = pd.to_datetime(["2020-01-06", "2020-01-07", "2020-01-08"])
    daily = pd.DataFrame(
        {"permno": [7, 7, 7], "date": list(dates),
         "ret": [0.01, 0.02, 0.03], "prc": [10.0, 10.0, 10.0], "vol": [1, 1, 1]}
    )
    # dlstcd=100 means "still trading" — must be ignored even if the date matches.
    delist = pd.DataFrame({"permno": [7], "dlstdt": [dates[1]], "dlret": [np.nan], "dlstcd": [100]})
    dcfg = {"missing_perf_dlret": -0.30, "perf_code_ranges": [[500, 500], [520, 584]]}
    out = load.apply_delisting_returns(daily, delist, dcfg)
    assert not out["delist_event"].any()                                   # active code ignored
    assert abs(out.loc[out.date == dates[1], "ret_adj"].iloc[0] - 0.02) < 1e-12  # return untouched


def test_duplicate_permno_date_raises():
    daily = pd.DataFrame(
        {
            "permno": [1, 1],
            "date": pd.to_datetime(["2020-01-06", "2020-01-06"]),  # duplicate key
            "ret": [0.01, 0.02],
        }
    )
    try:
        load._check_unique_permno_date(daily)
        assert False, "expected ValueError on duplicate (permno, date)"
    except ValueError:
        pass
