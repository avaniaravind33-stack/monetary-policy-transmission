"""
policy_surprise.py — Policy surprise analysis module.

Data limitations (critical, must be stated in research):
-----------------------------------------------------------
  Formal consensus survey data (Bloomberg/Reuters polls) for Indian MPC meetings
  is available publicly for a subset of meetings, particularly post-2017.
  For pre-MPC decisions (2014-2016), no organised consensus polling existed.

  The expected_bps values in rbi_events.py are sourced from:
    1. Reuters polls (published 1-2 weeks before MPC meetings, 2017+)
    2. Bloomberg survey medians where cross-referenced in press reports
    3. Where surveys are cited in RBI post-meeting press releases

  Where expected_bps = NaN, no reliable pre-meeting consensus is available.
  We do NOT impute, interpolate, or fabricate expectations.

  Surprise = Actual change − Expected change
  A positive surprise is "hawkish" (hike more / cut less than expected).
  A negative surprise is "dovish".

  For the policy-surprise regression, we study whether the magnitude of
  the surprise predicts the magnitude of market reactions:
    AR_asset,t0 = γ₀ + γ₁ · Surprise_t + η_t

  We also separate "in-line" (surprise ≈ 0) from "surprise" events and
  test whether AR mean differs between the two groups.
"""

import numpy as np
import pandas as pd
from scipy import stats


SURPRISE_THRESHOLD_BPS = 10.0  # surprises ≤ this magnitude treated as "in-line"


def classify_surprise(surprise_bps: float) -> str:
    """Classify a policy surprise into hawkish / dovish / in-line / unknown."""
    if pd.isna(surprise_bps):
        return "unknown"
    if abs(surprise_bps) <= SURPRISE_THRESHOLD_BPS:
        return "in-line"
    return "hawkish" if surprise_bps > 0 else "dovish"


def build_surprise_table(events: pd.DataFrame) -> pd.DataFrame:
    """
    Construct a clean surprise analysis table.

    Inputs: events DataFrame from rbi_events.get_full_calendar()
    Returns: DataFrame with surprise metrics, only for meetings with expectations.

    Columns:
      date, cycle, change_bps, expected_bps, surprise_bps,
      surprise_class, n_analysts, notes
    """
    df = events[events["has_expectations"]].copy()
    df = df[df["change_bps"] != 0].copy()  # focus on moves (not holds)

    df["surprise_class"] = df["surprise_bps"].apply(classify_surprise)

    out_cols = [
        "date", "cycle", "change_bps", "expected_bps",
        "surprise_bps", "surprise_class", "n_analysts", "notes"
    ]
    available = [c for c in out_cols if c in df.columns]
    result = df[available].copy().reset_index(drop=True)
    result["date"] = pd.to_datetime(result["date"])
    return result


def merge_surprise_with_cars(
    car_df: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join surprise data onto the CAR panel for events where expectations exist.
    Returns a merged DataFrame restricted to events with expectations data.
    """
    ev = events[events["has_expectations"]].copy()
    if "surprise_class" not in ev.columns:
        ev["surprise_class"] = ev["surprise_bps"].apply(classify_surprise)

    cols = [c for c in ["date", "surprise_bps", "surprise_class", "n_analysts"] if c in ev.columns]
    surprise_map = ev[cols].copy()
    surprise_map["date"] = pd.to_datetime(surprise_map["date"])
    car_df = car_df.copy()
    car_df["event_date"] = pd.to_datetime(car_df["event_date"])
    merged = car_df.merge(
        surprise_map.rename(columns={"date": "event_date"}),
        on="event_date",
        how="inner",
        suffixes=("", "_ev"),
    )
    return merged


def regress_surprise_on_car(
    merged: pd.DataFrame,
    asset: str,
    horizon: str,
) -> dict:
    """
    OLS regression: CAR = γ₀ + γ₁ · Surprise_bps + ε

    Parameters
    ----------
    merged  : output of merge_surprise_with_cars
    asset   : e.g. "Nifty50", "BankNifty", "GSec10Y", "USDINR"
    horizon : e.g. "CAR[+0,+0]", "CAR[+0,+1]"

    Returns
    -------
    dict with regression statistics
    """
    import statsmodels.api as sm

    sub = merged[(merged["asset"] == asset)].dropna(subset=["surprise_bps", horizon])
    if len(sub) < 5:
        return {
            "asset": asset, "horizon": horizon,
            "n": len(sub), "gamma0": np.nan, "gamma1": np.nan,
            "t_gamma1": np.nan, "p_gamma1": np.nan, "r_squared": np.nan,
            "note": "insufficient events with expectations",
        }

    X = sm.add_constant(sub["surprise_bps"].values.astype(float))
    Y = sub[horizon].values.astype(float)

    res = sm.OLS(Y, X).fit(cov_type="HC3")   # White-corrected

    return {
        "asset":     asset,
        "horizon":   horizon,
        "n":         int(res.nobs),
        "gamma0":    res.params[0],
        "gamma1":    res.params[1],
        "t_gamma0":  res.tvalues[0],
        "t_gamma1":  res.tvalues[1],
        "p_gamma1":  res.pvalues[1],
        "r_squared": res.rsquared,
        "significant_5pct": res.pvalues[1] < 0.05,
    }


def surprise_vs_inline_ttest(
    merged: pd.DataFrame,
    asset: str,
    horizon: str,
) -> dict:
    """
    Welch t-test: do surprise events show different CAR than in-line events?
    """
    sub = merged[merged["asset"] == asset].dropna(subset=["surprise_class", horizon])
    surprise_cars = sub[sub["surprise_class"].isin(["hawkish", "dovish"])][horizon].values
    inline_cars   = sub[sub["surprise_class"] == "in-line"][horizon].values

    if len(surprise_cars) < 3 or len(inline_cars) < 3:
        return {
            "note": f"insufficient events: n_surprise={len(surprise_cars)}, n_inline={len(inline_cars)}"
        }

    t_stat, p_val = stats.ttest_ind(surprise_cars, inline_cars, equal_var=False)
    return {
        "asset":              asset,
        "horizon":            horizon,
        "n_surprise":         len(surprise_cars),
        "n_inline":           len(inline_cars),
        "mean_surprise_car":  np.mean(surprise_cars),
        "mean_inline_car":    np.mean(inline_cars),
        "t_stat_welch":       t_stat,
        "p_value":            p_val,
        "significant_5pct":   p_val < 0.05,
    }


def get_notable_surprise_events(events: pd.DataFrame, threshold_bps: float = 25.0) -> pd.DataFrame:
    """
    Return events where |surprise| >= threshold_bps with context notes.
    These are the analytically most interesting cases.
    """
    df = events[events["has_expectations"] & (events["surprise_bps"].abs() >= threshold_bps)].copy()
    return df.sort_values("surprise_bps", key=abs, ascending=False).reset_index(drop=True)


def run_surprise_suite(
    car_df: pd.DataFrame,
    events: pd.DataFrame,
    assets: list = None,
    horizons: list = None,
) -> dict:
    """
    Run OLS surprise regressions and Welch t-tests across specified assets and horizons.
    """
    if assets is None:
        assets = ["Nifty50", "BankNifty", "GSec10Y", "USDINR"]
    if horizons is None:
        horizons = ["CAR[+0,+0]", "CAR[+0,+1]"]

    merged = merge_surprise_with_cars(car_df, events)
    reg_results = []
    ttest_results = []

    for a in assets:
        for h in horizons:
            if h in merged.columns:
                reg_results.append(regress_surprise_on_car(merged, a, h))
                ttest_results.append(surprise_vs_inline_ttest(merged, a, h))

    return {
        "merged_panel": merged,
        "regressions": pd.DataFrame(reg_results),
        "ttests": pd.DataFrame(ttest_results),
        "surprise_table": build_surprise_table(events),
        "notable_events": get_notable_surprise_events(events),
    }


if __name__ == "__main__":
    from src.rbi_events import get_full_calendar
    events = get_full_calendar()

    st = build_surprise_table(events)
    print("Surprise events (where expectations available):")
    print(st[["date","change_bps","expected_bps","surprise_bps","surprise_class"]].to_string())

    notable = get_notable_surprise_events(events)
    print(f"\nHigh-surprise events (|surprise| ≥ 25 bps):")
    print(notable[["date","cycle","change_bps","expected_bps","surprise_bps","notes"]].to_string())
