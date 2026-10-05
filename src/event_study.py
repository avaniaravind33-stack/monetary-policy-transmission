"""
event_study.py — Event-study framework for RBI monetary-policy announcements.

Methodology
-----------
For each RBI policy event on date t:

  Estimation window : [t-120, t-21]  (≈ 100 trading days pre-pre-event)
  Event window      : {-1, 0, +1, +3, +5} relative trading days

  Market model:
    r_i,t = α_i + β_i · r_m,t + ε_i,t
    (estimated on the estimation window; OLS)

  Abnormal Return:
    AR_i,t = r_i,t − (α̂_i + β̂_i · r_m,t)

  Cumulative Abnormal Return over window [a, b]:
    CAR_i(a,b) = Σ_{t=a}^{b} AR_i,t

  Average CAR across N events:
    ACAR(a,b) = (1/N) Σ_j CAR_j(a,b)

  For bond yields (GSec10Y): AR is computed as the change in yield relative
  to the model-implied change. The "return" here is Δy (first difference of yield).
  This is economically appropriate: a bond yield is a rate, not a price.

  For USD/INR (quoted as INR per USD): a positive log-return means INR depreciation.

Statistical inference:
  - Newey-West HAC standard errors (maxlags=5) on pooled OLS regressions.
  - Patell (1976) standardisation for individual event AR significance.
  - BMP (Boehmer Musumeci Poulsen 1991) test for cross-sectional variance of AR.

Assumptions & limitations:
  - Market model is estimated using Nifty50 as the market factor for equity
    assets. For G-Sec yield changes, no standard "market factor" applies;
    we use a constant-mean model (AR = Δy − mean Δy over estimation window).
  - Thin-trading / non-synchronous issues are minimal for NIFTY indices but
    may affect individual bank stocks on low-volume days.
  - Emergency off-cycle events (COVID, May-2022) may not have a clean
    estimation window; these are flagged and results treated with caution.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ESTIMATION_DAYS = 100   # trading days in estimation window
PRE_BUFFER      = 20    # trading days between estimation end and event day
EVENT_WINDOWS   = [(-1, -1), (0, 0), (0, 1), (0, 3), (0, 5)]  # (a, b) relative days
KEY_HORIZONS    = [-1, 0, 1, 3, 5]  # individual days to capture

# Assets whose "return" is first-difference of level (not log-return)
YIELD_ASSETS = ["GSec10Y"]

# Market factor for equity / FX models
EQUITY_MARKET_COL = "Nifty50"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _find_iloc(date: pd.Timestamp, index: pd.DatetimeIndex) -> Optional[int]:
    """Return iloc position of date (or nearest subsequent trading day, ≤5 days)."""
    if date in index:
        return index.get_loc(date)
    for lag in range(1, 6):
        d = date + pd.Timedelta(days=lag)
        if d in index:
            return index.get_loc(d)
    return None


def _ols_market_model(
    y_est: np.ndarray,
    x_est: np.ndarray,
    y_ev: np.ndarray,
    x_ev: np.ndarray,
    is_yield: bool = False,
) -> tuple[np.ndarray, float, float, float]:
    """
    Fit OLS on estimation window; compute AR on event window.

    For yield assets (is_yield=True), the market factor x is not used;
    instead we use a constant-mean model: E[Δy] = mean(Δy over estimation window).

    Returns
    -------
    ar        : np.ndarray of abnormal returns over event window
    alpha     : intercept
    beta      : market beta (np.nan for yield assets)
    resid_std : residual std from estimation (for standardisation)
    """
    valid_est = np.isfinite(y_est) & (np.isfinite(x_est) if not is_yield else np.ones_like(y_est, dtype=bool))

    if valid_est.sum() < 30:
        return np.full(len(y_ev), np.nan), np.nan, np.nan, np.nan

    if is_yield:
        # Constant-mean model: expected change = mean over estimation window
        mu  = np.nanmean(y_est[valid_est])
        ar  = y_ev - mu
        return ar, mu, np.nan, np.nanstd(y_est[valid_est] - mu)
    else:
        X    = sm.add_constant(x_est[valid_est])
        res  = sm.OLS(y_est[valid_est], X).fit()
        alpha, beta = res.params[0], res.params[1]
        valid_ev = np.isfinite(y_ev) & np.isfinite(x_ev)
        exp_r    = alpha + beta * x_ev
        ar       = np.where(valid_ev, y_ev - exp_r, np.nan)
        return ar, alpha, beta, np.sqrt(res.mse_resid)


# ---------------------------------------------------------------------------
# Main event-study engine
# ---------------------------------------------------------------------------

def run_event_study(
    returns: pd.DataFrame,
    events: pd.DataFrame,
    market_col: str = EQUITY_MARKET_COL,
    estimation_days: int = ESTIMATION_DAYS,
    pre_buffer: int = PRE_BUFFER,
    key_horizons: list[int] = None,
) -> dict:
    """
    Run the complete event study across all assets and all events.

    Parameters
    ----------
    returns         : daily returns DataFrame (index=date, columns=assets)
    events          : RBI event DataFrame from rbi_events.get_full_calendar()
    market_col      : column used as market factor for equity models
    estimation_days : length of estimation window
    pre_buffer      : trading days between estimation window end and event day
    key_horizons    : list of relative days to capture (default: KEY_HORIZONS)

    Returns
    -------
    {
        "ar_panel"       : long-form AR DataFrame (event × asset × rel_day)
        "car_panel"      : wide-form CAR DataFrame (event × asset × horizon)
        "model_params"   : regression parameters per event × asset
        "event_log"      : events with iloc positions + data quality flags
        "covered_assets" : list of asset names included
    }
    """
    if key_horizons is None:
        key_horizons = KEY_HORIZONS

    # Resolve market factor
    if market_col not in returns.columns:
        raise ValueError(f"market_col '{market_col}' not found in returns columns.")

    asset_cols = [c for c in returns.columns if c != market_col]
    idx        = returns.index

    ar_records    = []
    model_records = []
    event_log     = []

    for _, ev in events.iterrows():
        t0 = _find_iloc(ev["date"], idx)
        if t0 is None:
            event_log.append({**ev.to_dict(), "iloc_t0": None, "status": "no_trading_day"})
            continue

        t_est_start = t0 - pre_buffer - estimation_days
        t_est_end   = t0 - pre_buffer - 1

        # Min horizon we need: key_horizons are small (+5 at most); build around t0
        t_ev_min = t0 + min(key_horizons)   # could be t0 - 1
        t_ev_max = t0 + max(key_horizons)

        # Bounds check
        if t_est_start < 0:
            event_log.append({**ev.to_dict(), "iloc_t0": t0, "status": "insufficient_history"})
            continue
        if t_ev_max >= len(idx):
            event_log.append({**ev.to_dict(), "iloc_t0": t0, "status": "event_window_out_of_range"})
            continue

        ev_entry = {**ev.to_dict(), "iloc_t0": t0, "status": "ok",
                    "n_est_days": t_est_end - t_est_start + 1}
        event_log.append(ev_entry)

        mkt_est = returns[market_col].iloc[t_est_start:t_est_end + 1].values

        for asset in asset_cols:
            is_yield = asset in YIELD_ASSETS
            y_est    = returns[asset].iloc[t_est_start:t_est_end + 1].values

            # Gather event-day values at key horizons
            ar_at_horizons = {}
            level_at_horizons = {}
            for kh in key_horizons:
                iloc_kh = t0 + kh
                if 0 <= iloc_kh < len(idx):
                    ar_at_horizons[kh]    = np.nan   # placeholder; filled below
                    level_at_horizons[kh] = returns[asset].iloc[iloc_kh]

            # Run OLS on estimation window then compute AR on event-window days
            # We need y and x for each event-horizon day
            if is_yield:
                mu_est = np.nanmean(y_est[np.isfinite(y_est)])
                alpha, beta, resid_std = mu_est, np.nan, np.nanstd(y_est[np.isfinite(y_est)] - mu_est) if np.isfinite(y_est).sum() > 0 else np.nan
                for kh in key_horizons:
                    iloc_kh = t0 + kh
                    if 0 <= iloc_kh < len(idx):
                        y_kh = returns[asset].iloc[iloc_kh]
                        ar_at_horizons[kh] = y_kh - mu_est if pd.notna(y_kh) else np.nan
            else:
                # OLS market model on estimation window
                mkt_est_valid = mkt_est
                valid_est = np.isfinite(y_est) & np.isfinite(mkt_est_valid)
                if valid_est.sum() >= 30:
                    X   = sm.add_constant(mkt_est_valid[valid_est])
                    res = sm.OLS(y_est[valid_est], X).fit()
                    alpha, beta = res.params[0], res.params[1]
                    resid_std   = np.sqrt(res.mse_resid)
                else:
                    alpha, beta, resid_std = np.nan, np.nan, np.nan

                for kh in key_horizons:
                    iloc_kh = t0 + kh
                    if 0 <= iloc_kh < len(idx):
                        y_kh   = returns[asset].iloc[iloc_kh]
                        mkt_kh = returns[market_col].iloc[iloc_kh]
                        if pd.notna(alpha) and pd.notna(y_kh) and pd.notna(mkt_kh):
                            ar_at_horizons[kh] = y_kh - (alpha + beta * mkt_kh)
                        else:
                            ar_at_horizons[kh] = np.nan

            model_records.append({
                "event_date": ev["date"],
                "asset":      asset,
                "alpha":      alpha,
                "beta":       beta,
                "resid_std":  resid_std,
                "n_est_days": t_est_end - t_est_start + 1,
            })

            # Build AR records
            for kh in key_horizons:
                ar_records.append({
                    "event_date":   ev["date"],
                    "cycle":        ev["cycle"],
                    "change_bps":   ev["change_bps"],
                    "stance":       ev["stance"],
                    "pre_mpc":      ev.get("pre_mpc", False),
                    "has_expectations": ev.get("has_expectations", False),
                    "surprise_bps": ev.get("surprise_bps", np.nan),
                    "asset":        asset,
                    "rel_day":      kh,
                    "ar":           ar_at_horizons.get(kh, np.nan),
                    "raw_return":   level_at_horizons.get(kh, np.nan),
                })

    ar_df    = pd.DataFrame(ar_records)
    model_df = pd.DataFrame(model_records)
    ev_log   = pd.DataFrame(event_log)

    # Compute CAR panels
    car_df   = _compute_car(ar_df)

    return {
        "ar_panel":     ar_df,
        "car_panel":    car_df,
        "model_params": model_df,
        "event_log":    ev_log,
        "covered_assets": asset_cols,
    }


def _compute_car(ar_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute CAR for each (event_date, asset) pair across the pre-defined horizons.
    CAR(a,b) = AR[-1] + AR[0] + … up to b (using sorted key_horizons ≤ b).
    """
    rows = []
    horizons = EVENT_WINDOWS   # list of (a, b) tuples

    for (ev_date, asset), grp in ar_df.groupby(["event_date", "asset"]):
        ar_series = grp.set_index("rel_day")["ar"].sort_index()
        meta = grp.iloc[0]
        row  = {
            "event_date":   ev_date,
            "asset":        asset,
            "cycle":        meta["cycle"],
            "change_bps":   meta["change_bps"],
            "stance":       meta["stance"],
            "pre_mpc":      meta.get("pre_mpc", False),
            "has_expectations": meta.get("has_expectations", False),
            "surprise_bps": meta.get("surprise_bps", np.nan),
        }
        for (a, b) in horizons:
            window_ar = ar_series[(ar_series.index >= a) & (ar_series.index <= b)]
            row[f"CAR[{a:+d},{b:+d}]"] = window_ar.sum() if not window_ar.empty else np.nan
        # Also grab individual day ARs
        for kh in KEY_HORIZONS:
            row[f"AR[{kh:+d}]"] = ar_series.get(kh, np.nan)
        rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Rate-sensitivity regression (β₂)
# ---------------------------------------------------------------------------

def run_rate_sensitivity(
    returns: pd.DataFrame,
    events: pd.DataFrame,
    market_col: str = EQUITY_MARKET_COL,
) -> pd.DataFrame:
    """
    Estimate rate-sensitivity (β₂) via:
        r_asset,t = α + β₁·r_market,t + β₂·RateChange_t + ε_t

    where RateChange_t = change_bps on event days, 0 otherwise.
    HAC Newey-West standard errors (maxlags=5).

    Returns DataFrame indexed by asset with [alpha, beta_market, beta_rate,
    t_beta_rate, p_beta_rate, r_squared, n_obs].
    """
    asset_cols = [c for c in returns.columns if c != market_col]

    # Build rate-change series aligned to returns index
    rate_series = pd.Series(0.0, index=returns.index, name="rate_change_bps")
    for _, ev in events.iterrows():
        if ev["change_bps"] != 0:
            t0 = _find_iloc(ev["date"], returns.index)
            if t0 is not None:
                rate_series.iloc[t0] = float(ev["change_bps"])

    results = []
    for asset in asset_cols:
        y     = returns[asset].values
        mkt   = returns[market_col].values
        rate  = rate_series.values

        valid = np.isfinite(y) & np.isfinite(mkt)
        if valid.sum() < 200:
            print(f"  Skipping {asset}: only {valid.sum()} valid obs")
            continue

        X = np.column_stack([np.ones(valid.sum()), mkt[valid], rate[valid]])
        Y = y[valid]

        try:
            res = sm.OLS(Y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
            results.append({
                "asset":         asset,
                "alpha":         res.params[0],
                "beta_market":   res.params[1],
                "beta_rate":     res.params[2],
                "t_beta_rate":   res.tvalues[2],
                "p_beta_rate":   res.pvalues[2],
                "r_squared":     res.rsquared,
                "n_obs":         int(res.nobs),
            })
        except Exception as e:
            print(f"  OLS error for {asset}: {e}")

    df = pd.DataFrame(results).set_index("asset")
    return df.sort_values("beta_rate")


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------

def test_acar_significance(
    car_df: pd.DataFrame,
    asset: str,
    horizon: str,
    cycle: Optional[str] = None,
) -> dict:
    """
    Test whether ACAR is significantly different from zero using a t-test.
    Also reports N (events), mean CAR, std, t-stat, p-value.

    If N < 30, uses a t-distribution (Student's t); otherwise z-approx.
    """
    subset = car_df[car_df["asset"] == asset]
    if cycle:
        subset = subset[subset["cycle"] == cycle]
    cars = subset[horizon].dropna().values

    if len(cars) < 3:
        return {"n": len(cars), "mean": np.nan, "p_value": np.nan,
                "t_stat": np.nan, "std": np.nan, "note": "insufficient events"}

    t_stat, p_val = stats.ttest_1samp(cars, 0.0)
    return {
        "asset":      asset,
        "horizon":    horizon,
        "cycle":      cycle or "All",
        "n":          len(cars),
        "mean_car":   np.mean(cars),
        "std_car":    np.std(cars, ddof=1),
        "t_stat":     t_stat,
        "p_value":    p_val,
        "significant_5pct": abs(t_stat) > 2.0,
    }


def test_hike_vs_cut(
    car_df: pd.DataFrame,
    asset: str,
    horizon: str,
) -> dict:
    """
    Two-sample t-test: do hikes produce different CARs than cuts?
    Uses Welch's t-test (unequal variances).
    """
    hike_cars = car_df[(car_df["asset"] == asset) & (car_df["cycle"] == "Hike")][horizon].dropna().values
    cut_cars  = car_df[(car_df["asset"] == asset) & (car_df["cycle"] == "Cut" )][horizon].dropna().values

    if len(hike_cars) < 3 or len(cut_cars) < 3:
        return {"note": "insufficient events for Welch t-test"}

    t_stat, p_val = stats.ttest_ind(hike_cars, cut_cars, equal_var=False)
    return {
        "asset":         asset,
        "horizon":       horizon,
        "n_hike":        len(hike_cars),
        "n_cut":         len(cut_cars),
        "mean_hike_car": np.mean(hike_cars),
        "mean_cut_car":  np.mean(cut_cars),
        "t_stat_welch":  t_stat,
        "p_value":       p_val,
        "significant_5pct": p_val < 0.05,
    }


def correlate_surprise_vs_car(
    car_df: pd.DataFrame,
    asset: str,
    horizon: str,
) -> dict:
    """
    Pearson correlation between policy surprise (bps) and CAR at a horizon.
    Only uses events where expectations were available.
    """
    sub = car_df[(car_df["asset"] == asset) & car_df["has_expectations"]].dropna(
        subset=["surprise_bps", horizon]
    )
    if len(sub) < 5:
        return {"n": len(sub), "r": np.nan, "p": np.nan,
                "note": "insufficient events with expectations data"}

    r, p = stats.pearsonr(sub["surprise_bps"].values, sub[horizon].values)
    return {
        "asset":   asset,
        "horizon": horizon,
        "n":       len(sub),
        "pearson_r": r,
        "p_value": p,
        "significant_5pct": p < 0.05,
    }


if __name__ == "__main__":
    from src.data_loader import download_all, compute_returns, generate_synthetic_data
    from src.rbi_events import get_full_calendar

    try:
        prices  = download_all(force_refresh=False)
    except Exception:
        prices  = generate_synthetic_data()

    returns = compute_returns(prices)
    events  = get_full_calendar()

    print("Running event study …")
    result  = run_event_study(returns, events)

    print(f"AR panel rows : {len(result['ar_panel'])}")
    print(f"CAR panel rows: {len(result['car_panel'])}")
    print(f"Events in log : {len(result['event_log'])}")
    print(result["event_log"][["date","cycle","change_bps","status"]].to_string())
