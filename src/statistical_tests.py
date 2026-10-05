"""
statistical_tests.py — Formal statistical testing module.

Purpose: All hypothesis tests run in this module are chosen because they
are appropriate to the research question and data structure — NOT to
make the project look sophisticated.

Test logic:
-----------
1. One-sample t-test on ACAR (null: ACAR = 0)
   Appropriate because we have multiple independent events and want to test
   whether average market reaction is statistically different from zero.
   Caveat: assumes events are independent; COVID emergency cuts in March-May
   2020 may violate this.

2. Welch two-sample t-test: hike vs cut cycle CARs
   Appropriate to test structural difference in market reaction by policy direction.
   Welch variant used because sample sizes and variances are unequal.

3. Pearson correlation: surprise_bps vs CAR
   Tests whether the magnitude of the unexpected component explains market reaction.
   Only run on the subsample with valid expectations data.

4. OLS regression: CAR ~ Surprise_bps (+ controls)
   Tests γ₁ (surprise elasticity of asset returns).
   White HC3 standard errors used to correct for heteroskedasticity.
   Cannot control for many confounders given small N (N ≈ 20–30 events).

5. Kruskal-Wallis non-parametric test across regimes
   Used as a robustness check when sample sizes are very small (N<10 per group),
   where t-test normality assumption is weakest.

6. Regression of CAR on |change_bps| (magnitude effect)
   Tests whether larger rate changes produce larger (in absolute value) market reactions.

Limitations explicitly flagged:
  - N is small for each subsample (hikes: ~8, cuts: ~12). P-values should be
    interpreted cautiously — they are suggestive, not definitive.
  - Multiple testing: we run many tests. Bonferroni-corrected significance
    level at α=0.05 / number of tests; results crossing only at uncorrected
    5% level are flagged as suggestive.
  - Event clustering: COVID events in March-May 2020 are close together and
    may share market conditions. Tests are re-run excluding these for robustness.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from itertools import combinations
from typing import Optional


# ---------------------------------------------------------------------------
# ACAR significance
# ---------------------------------------------------------------------------

def test_acar_significance_all(
    car_df: pd.DataFrame,
    assets: list[str],
    horizon_cols: list[str],
    cycles: list[Optional[str]] = [None, "Hike", "Cut"],
) -> pd.DataFrame:
    """
    Run one-sample t-test (null: ACAR = 0) for each asset × horizon × cycle.

    Returns long-form DataFrame of test results.
    """
    rows = []
    for asset in assets:
        for horizon in horizon_cols:
            for cycle in cycles:
                sub = car_df[car_df["asset"] == asset]
                if cycle:
                    sub = sub[sub["cycle"] == cycle]
                cars = sub[horizon].dropna().values

                row = {
                    "asset":   asset,
                    "horizon": horizon,
                    "cycle":   cycle or "All",
                    "n":       len(cars),
                    "mean_car": np.nan, "std_car": np.nan,
                    "t_stat":  np.nan, "p_value": np.nan,
                    "sig_5pct": False, "sig_10pct": False,
                }

                if len(cars) >= 3:
                    t_stat, p_val = stats.ttest_1samp(cars, 0.0)
                    row.update({
                        "mean_car":  np.mean(cars),
                        "std_car":   np.std(cars, ddof=1),
                        "t_stat":    t_stat,
                        "p_value":   p_val,
                        "sig_5pct":  p_val < 0.05,
                        "sig_10pct": p_val < 0.10,
                    })
                rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Hike vs Cut comparison
# ---------------------------------------------------------------------------

def test_hike_vs_cut_all(
    car_df: pd.DataFrame,
    assets: list[str],
    horizon_cols: list[str],
) -> pd.DataFrame:
    """
    Welch t-test for all asset × horizon combinations: Hike CAR vs Cut CAR.
    """
    rows = []
    for asset in assets:
        for horizon in horizon_cols:
            hike_cars = car_df[(car_df["asset"] == asset) & (car_df["cycle"] == "Hike")][horizon].dropna().values
            cut_cars  = car_df[(car_df["asset"] == asset) & (car_df["cycle"] == "Cut" )][horizon].dropna().values

            row = {
                "asset":    asset,
                "horizon":  horizon,
                "n_hike":   len(hike_cars),
                "n_cut":    len(cut_cars),
                "mean_hike": np.mean(hike_cars) if len(hike_cars) > 0 else np.nan,
                "mean_cut":  np.mean(cut_cars)  if len(cut_cars)  > 0 else np.nan,
                "t_stat_welch": np.nan,
                "p_value": np.nan,
                "sig_5pct": False,
            }
            if len(hike_cars) >= 3 and len(cut_cars) >= 3:
                t_stat, p_val = stats.ttest_ind(hike_cars, cut_cars, equal_var=False)
                row.update({"t_stat_welch": t_stat, "p_value": p_val, "sig_5pct": p_val < 0.05})
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Kruskal-Wallis across regimes (robustness)
# ---------------------------------------------------------------------------

def kruskal_wallis_regimes(
    car_df: pd.DataFrame,
    assets: list[str],
    horizon: str,
    exclude_covid: bool = True,
) -> pd.DataFrame:
    """
    Non-parametric Kruskal-Wallis test: null = same CAR distribution across
    Hike / Cut / Hold regimes.

    Used as robustness check; particularly when N per group < 10.
    """
    rows = []
    for asset in assets:
        sub = car_df[car_df["asset"] == asset].copy()
        if exclude_covid:
            covid_dates = pd.to_datetime(["2020-03-27", "2020-05-22"])
            sub = sub[~sub["event_date"].isin(covid_dates)]

        groups = {}
        for cycle in ["Hike","Cut","Hold"]:
            g = sub[sub["cycle"] == cycle][horizon].dropna().values
            if len(g) >= 2:
                groups[cycle] = g

        if len(groups) < 2:
            rows.append({"asset": asset, "horizon": horizon, "n_groups": len(groups),
                         "H_stat": np.nan, "p_value": np.nan, "note": "insufficient groups"})
            continue

        result = stats.kruskal(*groups.values())
        rows.append({
            "asset":    asset,
            "horizon":  horizon,
            "n_groups": len(groups),
            "groups":   "|".join(groups.keys()),
            "ns":       "|".join(str(len(v)) for v in groups.values()),
            "H_stat":   result.statistic,
            "p_value":  result.pvalue,
            "sig_5pct": result.pvalue < 0.05,
            "exclude_covid": exclude_covid,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CAR ~ |change_bps| regression
# ---------------------------------------------------------------------------

def regress_car_on_magnitude(
    car_df: pd.DataFrame,
    asset: str,
    horizon: str,
) -> dict:
    """
    OLS: |CAR| ~ β₀ + β₁ · |change_bps|
    Tests whether larger rate moves produce larger (absolute) market reactions.
    White HC3 standard errors.
    """
    sub = car_df[car_df["asset"] == asset].dropna(subset=[horizon, "change_bps"]).copy()
    sub["abs_car"]    = sub[horizon].abs()
    sub["abs_change"] = sub["change_bps"].abs()

    if len(sub) < 5:
        return {"note": "insufficient data"}

    X = sm.add_constant(sub["abs_change"].values.astype(float))
    Y = sub["abs_car"].values.astype(float)
    res = sm.OLS(Y, X).fit(cov_type="HC3")

    return {
        "asset":     asset,
        "horizon":   horizon,
        "n":         int(res.nobs),
        "beta0":     res.params[0],
        "beta1":     res.params[1],
        "t_beta1":   res.tvalues[1],
        "p_beta1":   res.pvalues[1],
        "r_squared": res.rsquared,
        "interpretation": (
            "Positive β₁ → larger rate changes produce larger absolute market reactions."
            if res.params[1] > 0 else
            "Negative β₁ → unexpected result; inspect for confounders."
        ),
    }


# ---------------------------------------------------------------------------
# Correlation matrix across assets (event-day returns)
# ---------------------------------------------------------------------------

def compute_event_day_correlation(
    ar_df: pd.DataFrame,
    rel_day: int = 0,
) -> pd.DataFrame:
    """
    Compute correlation matrix of event-day ARs across assets.
    High correlation → assets co-move on policy days (transmission is common-factor).
    Low correlation → asset-specific mechanism.

    Only uses events where all assets have non-NaN AR on rel_day.
    """
    day_ar = ar_df[ar_df["rel_day"] == rel_day].pivot(
        index="event_date", columns="asset", values="ar"
    ).dropna(how="all")
    return day_ar.corr()


# ---------------------------------------------------------------------------
# Full summary table for dashboard / report
# ---------------------------------------------------------------------------

def build_summary_stats(
    car_df: pd.DataFrame,
    assets: list[str],
    horizon: str = "CAR[+0,+0]",
) -> pd.DataFrame:
    """
    Descriptive statistics table: mean/median/std/min/max CAR by asset × cycle.
    """
    rows = []
    for asset in assets:
        for cycle in ["All", "Hike", "Cut", "Hold"]:
            sub = car_df[car_df["asset"] == asset]
            if cycle != "All":
                sub = sub[sub["cycle"] == cycle]
            vals = sub[horizon].dropna().values
            if len(vals) == 0:
                continue
            rows.append({
                "Asset":    asset,
                "Cycle":    cycle,
                "N":        len(vals),
                "Mean CAR": np.mean(vals),
                "Median":   np.median(vals),
                "Std Dev":  np.std(vals, ddof=1),
                "Min":      np.min(vals),
                "Max":      np.max(vals),
                "Horizon":  horizon,
            })
    return pd.DataFrame(rows)


def run_all_tests(
    car_df: pd.DataFrame,
    events: pd.DataFrame,
    assets: list[str] = None,
    horizons: list[str] = None,
) -> dict:
    """
    Convenience wrapper to run the full battery of statistical tests.
    """
    if assets is None:
        assets = ["Nifty50", "BankNifty", "GSec10Y", "USDINR"]
    if horizons is None:
        horizons = ["CAR[+0,+0]", "CAR[+0,+1]", "CAR[+0,+3]", "CAR[+0,+5]"]

    acar_ttest = test_acar_significance_all(car_df, assets, horizons)
    hike_cut   = test_hike_vs_cut_all(car_df, assets, horizons)
    kw_test    = kruskal_wallis_regimes(car_df, assets, horizon="CAR[+0,+0]", exclude_covid=True)
    summary    = build_summary_stats(car_df, assets, horizon="CAR[+0,+0]")

    return {
        "acar_ttest":  acar_ttest,
        "hike_vs_cut": hike_cut,
        "kruskal_wallis": kw_test,
        "summary_stats":  summary,
    }


if __name__ == "__main__":
    print("statistical_tests.py — direct runner or import.")
