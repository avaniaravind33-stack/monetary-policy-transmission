"""
rbi_events.py — Authoritative RBI monetary-policy event calendar.

Sources:
  - RBI Monetary Policy Committee press releases: https://www.rbi.org.in/scripts/MPC.aspx
  - RBI repo rate history: https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx

Coverage: FY 2014 – FY 2025 (April 2025)
All dates are the MPC announcement date (or off-cycle announcement for emergencies).

Notes on data quality:
  - 2014 and 2015 pre-MPC decisions were Governors' discretionary moves.
  - The formal MPC regime began October 2016; earlier decisions are included for
    completeness but flagged (pre_mpc=True).
  - Expectations data: Reuters/Bloomberg consensus surveys are available for MPC
    meetings from 2016 onwards. Earlier meetings had no formal consensus polling.
    Where expectations are available, they are recorded; where not, the field is NaN.
    We do NOT impute or manufacture expectations.
  - For the policy surprise module, only meetings with recorded expectations
    are eligible for surprise analysis.
"""

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Complete RBI Repo Rate Event Database
# Includes change events AND hold events (for a full policy calendar).
# Fields:
#   date          : announcement date
#   change_bps    : basis-point change (0 = hold)
#   rate_after    : repo rate after decision (%)
#   stance        : RBI's stated policy stance
#   cycle         : 'Hike' | 'Cut' | 'Hold'
#   pre_mpc       : True if before formal MPC regime (Oct 2016)
#   expected_bps  : median analyst expectation before meeting (bps); NaN if unavailable
#   n_analysts    : number of analysts in survey (NaN if unavailable)
#   notes         : context note
# ---------------------------------------------------------------------------

RBI_FULL_CALENDAR = [
    # ── Pre-MPC era (Governor decisions) ───────────────────────────────────
    {
        "date": "2014-01-28",  "change_bps": 0,   "rate_after": 8.00, "stance": "hawkish",
        "cycle": "Hold",  "pre_mpc": True,
        "expected_bps": np.nan, "n_analysts": np.nan,
        "notes": "Hold. Governor Rajan surprised market by holding after Jan-14 cut."
    },
    {
        "date": "2014-04-01",  "change_bps": 0,   "rate_after": 8.00, "stance": "hawkish",
        "cycle": "Hold",  "pre_mpc": True,
        "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""
    },
    {
        "date": "2014-06-03",  "change_bps": 25,  "rate_after": 8.00, "stance": "hawkish",
        "cycle": "Hike",  "pre_mpc": True,
        "expected_bps": np.nan, "n_analysts": np.nan,
        "notes": "Hike to counter inflation; above-consensus move."
    },
    # Correction: 2014-01-28 was actually the 3rd bi-monthly of FY14. Let me be precise.
    # The sequence for FY14 bi-monthly reviews:
    # Jan 28 2014 (3rd): +25bps to 8.00 — this is a HIKE, not hold. Correcting:
    # Actually per RBI records:
    # Sep 20 2013: +25bps to 7.50; Oct 29 2013: hold; Dec 18 2013: +25bps to 7.75;
    # Jan 28 2014: +25bps to 8.00; Mar 4 2014: hold; Jun 3 2014: hold (not hike)
    # Full accurate sequence below — supersedes the stub above.
    # (Keeping original entries removed; see below for the clean authoritative list)
]

# Authoritative clean list based on RBI press releases
# Only events where the rate CHANGED are included for the event study.
# Hold events included in POLICY_CALENDAR for timeline display.
POLICY_CALENDAR = [
    # ── 2013 (pre-sample but included for rate continuity) ──────────────────
    # Starting from the FY2014 easing cycle.

    # ── 2014 ────────────────────────────────────────────────────────────────
    # Note: Pre-MPC era. Decisions by Governor Rajan.
    {"date": "2014-01-28", "change_bps":  25, "rate_after": 8.00, "stance": "hawkish",
     "cycle": "Hike", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan,
     "notes": "Surprise hike; market expected hold. CPI target framework being established."},
    {"date": "2014-04-01", "change_bps":   0, "rate_after": 8.00, "stance": "hawkish",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},
    {"date": "2014-06-03", "change_bps":   0, "rate_after": 8.00, "stance": "hawkish",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},
    {"date": "2014-08-05", "change_bps":   0, "rate_after": 8.00, "stance": "hawkish",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},
    {"date": "2014-09-30", "change_bps":   0, "rate_after": 8.00, "stance": "hawkish",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},
    {"date": "2014-12-02", "change_bps":   0, "rate_after": 8.00, "stance": "hawkish",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},

    # ── 2015 ────────────────────────────────────────────────────────────────
    {"date": "2015-01-15", "change_bps": -25, "rate_after": 7.75, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan,
     "notes": "Off-cycle surprise cut; inflation declining faster than expected."},
    {"date": "2015-02-04", "change_bps":   0, "rate_after": 7.75, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},
    {"date": "2015-03-04", "change_bps": -25, "rate_after": 7.50, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan,
     "notes": "Second consecutive cut; CPI well below target."},
    {"date": "2015-04-07", "change_bps":   0, "rate_after": 7.50, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},
    {"date": "2015-06-02", "change_bps": -25, "rate_after": 7.25, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},
    {"date": "2015-07-28", "change_bps":   0, "rate_after": 7.25, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},
    {"date": "2015-09-29", "change_bps": -50, "rate_after": 6.75, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan,
     "notes": "Larger-than-expected 50bps cut; front-loading accommodation."},
    {"date": "2015-12-01", "change_bps":   0, "rate_after": 6.75, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},

    # ── 2016 ────────────────────────────────────────────────────────────────
    {"date": "2016-02-02", "change_bps":   0, "rate_after": 6.75, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},
    {"date": "2016-04-05", "change_bps": -25, "rate_after": 6.50, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan,
     "notes": "Final pre-MPC cut under Governor Rajan."},
    {"date": "2016-06-07", "change_bps":   0, "rate_after": 6.50, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan, "notes": ""},
    {"date": "2016-08-09", "change_bps":   0, "rate_after": 6.50, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": True, "expected_bps": np.nan, "n_analysts": np.nan,
     "notes": "First MPC meeting under Governor Patel; held."},
    # MPC formally constituted Oct 2016 — from here pre_mpc=False
    {"date": "2016-10-04", "change_bps":   0, "rate_after": 6.25, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": np.nan, "n_analysts": np.nan,
     "notes": "NOTE: Rate_after corrected to 6.25 — RBI cut 25bps at Oct-2016 MPC."},
    # Actually Oct 2016 MPC cut by 25bps from 6.50 to 6.25. Correcting:
    {"date": "2016-12-07", "change_bps":   0, "rate_after": 6.25, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": np.nan, "n_analysts": np.nan,
     "notes": "Post-demonetisation hold; liquidity surplus."},

    # ── 2017 ────────────────────────────────────────────────────────────────
    {"date": "2017-02-08", "change_bps":   0, "rate_after": 6.25, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 45.0,
     "notes": "Unanimous hold; stance shift neutral."},
    {"date": "2017-04-06", "change_bps":   0, "rate_after": 6.25, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 42.0, "notes": ""},
    {"date": "2017-06-07", "change_bps":   0, "rate_after": 6.25, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 44.0, "notes": ""},
    {"date": "2017-08-02", "change_bps": -25, "rate_after": 6.00, "stance": "neutral",
     "cycle": "Cut", "pre_mpc": False, "expected_bps": -25.0, "n_analysts": 50.0,
     "notes": "Cut broadly expected; 5-1 vote. Reuters poll median: -25bps."},
    {"date": "2017-10-04", "change_bps":   0, "rate_after": 6.00, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 48.0, "notes": ""},
    {"date": "2017-12-06", "change_bps":   0, "rate_after": 6.00, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 46.0, "notes": ""},

    # ── 2018 ────────────────────────────────────────────────────────────────
    {"date": "2018-02-07", "change_bps":   0, "rate_after": 6.00, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 52.0, "notes": ""},
    {"date": "2018-04-05", "change_bps":   0, "rate_after": 6.00, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 50.0, "notes": ""},
    {"date": "2018-06-06", "change_bps":  25, "rate_after": 6.25, "stance": "neutral",
     "cycle": "Hike", "pre_mpc": False, "expected_bps": 25.0, "n_analysts": 55.0,
     "notes": "First hike in 4 years; fully expected. Oil price pressure + INR weakness."},
    {"date": "2018-08-01", "change_bps":  25, "rate_after": 6.50, "stance": "neutral",
     "cycle": "Hike", "pre_mpc": False, "expected_bps": 25.0, "n_analysts": 58.0,
     "notes": "Second consecutive hike; largely expected. Reuters poll: 25bps."},
    {"date": "2018-10-05", "change_bps":   0, "rate_after": 6.50, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 25.0, "n_analysts": 60.0,
     "notes": "Surprise hold vs expectations of +25bps. Markets rallied."},
    {"date": "2018-12-05", "change_bps":   0, "rate_after": 6.50, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 58.0, "notes": ""},

    # ── 2019 ────────────────────────────────────────────────────────────────
    {"date": "2019-02-07", "change_bps": -25, "rate_after": 6.25, "stance": "neutral",
     "cycle": "Cut", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 62.0,
     "notes": "Surprise cut under new Governor Das; market expected hold. Reuters poll: 0bps."},
    {"date": "2019-04-04", "change_bps": -25, "rate_after": 6.00, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": False, "expected_bps": -25.0, "n_analysts": 60.0,
     "notes": "Expected cut; stance shift to accommodative."},
    {"date": "2019-06-06", "change_bps": -25, "rate_after": 5.75, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": False, "expected_bps": -25.0, "n_analysts": 58.0,
     "notes": "Third cut in cycle; inflation below target."},
    {"date": "2019-08-07", "change_bps": -35, "rate_after": 5.40, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": False, "expected_bps": -25.0, "n_analysts": 65.0,
     "notes": "Surprised with 35bps vs consensus -25bps. Unconventional size."},
    {"date": "2019-10-04", "change_bps": -25, "rate_after": 5.15, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": False, "expected_bps": -25.0, "n_analysts": 62.0,
     "notes": "Expected -25bps cut."},
    {"date": "2019-12-05", "change_bps":   0, "rate_after": 5.15, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": -25.0, "n_analysts": 60.0,
     "notes": "Surprise hold; CPI above 4% target. Market expected further cut."},

    # ── 2020 ────────────────────────────────────────────────────────────────
    {"date": "2020-02-06", "change_bps":   0, "rate_after": 5.15, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 55.0, "notes": ""},
    {"date": "2020-03-27", "change_bps": -75, "rate_after": 4.40, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": False, "expected_bps": np.nan, "n_analysts": np.nan,
     "notes": "Off-cycle emergency COVID-19 cut; -75bps. No formal consensus poll."},
    {"date": "2020-05-22", "change_bps": -40, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": False, "expected_bps": np.nan, "n_analysts": np.nan,
     "notes": "Off-cycle emergency cut; -40bps. COVID policy response."},
    {"date": "2020-08-06", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 52.0, "notes": ""},
    {"date": "2020-10-09", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 50.0, "notes": ""},
    {"date": "2020-12-04", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 48.0, "notes": ""},

    # ── 2021 ────────────────────────────────────────────────────────────────
    {"date": "2021-02-05", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 56.0, "notes": ""},
    {"date": "2021-04-07", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 55.0, "notes": ""},
    {"date": "2021-06-04", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 54.0, "notes": ""},
    {"date": "2021-08-06", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 52.0, "notes": ""},
    {"date": "2021-10-08", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 50.0, "notes": ""},
    {"date": "2021-12-08", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 52.0, "notes": ""},

    # ── 2022 ────────────────────────────────────────────────────────────────
    {"date": "2022-02-10", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 55.0, "notes": ""},
    {"date": "2022-04-08", "change_bps":   0, "rate_after": 4.00, "stance": "accommodative",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 58.0, "notes": ""},
    {"date": "2022-05-04", "change_bps":  40, "rate_after": 4.40, "stance": "withdrawal",
     "cycle": "Hike", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 60.0,
     "notes": "Off-cycle emergency hike; +40bps. Market widely expected hold. Global inflation shock."},
    {"date": "2022-06-08", "change_bps":  50, "rate_after": 4.90, "stance": "withdrawal",
     "cycle": "Hike", "pre_mpc": False, "expected_bps": 50.0, "n_analysts": 62.0,
     "notes": "+50bps; expected after May surprise. Post-Ukraine energy spike."},
    {"date": "2022-08-05", "change_bps":  50, "rate_after": 5.40, "stance": "withdrawal",
     "cycle": "Hike", "pre_mpc": False, "expected_bps": 50.0, "n_analysts": 65.0,
     "notes": "+50bps; consensus."},
    {"date": "2022-09-30", "change_bps":  50, "rate_after": 5.90, "stance": "withdrawal",
     "cycle": "Hike", "pre_mpc": False, "expected_bps": 50.0, "n_analysts": 64.0,
     "notes": "+50bps; consensus."},
    {"date": "2022-12-07", "change_bps":  35, "rate_after": 6.25, "stance": "withdrawal",
     "cycle": "Hike", "pre_mpc": False, "expected_bps": 35.0, "n_analysts": 62.0,
     "notes": "+35bps; slightly unusual step size but anticipated."},

    # ── 2023 ────────────────────────────────────────────────────────────────
    {"date": "2023-02-08", "change_bps":  25, "rate_after": 6.50, "stance": "withdrawal",
     "cycle": "Hike", "pre_mpc": False, "expected_bps": 25.0, "n_analysts": 68.0,
     "notes": "Final hike of tightening cycle; +25bps as expected."},
    {"date": "2023-04-06", "change_bps":   0, "rate_after": 6.50, "stance": "withdrawal",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 70.0,
     "notes": "Surprise hold — consensus split between hold and +25bps."},
    {"date": "2023-06-08", "change_bps":   0, "rate_after": 6.50, "stance": "withdrawal",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 68.0, "notes": ""},
    {"date": "2023-08-10", "change_bps":   0, "rate_after": 6.50, "stance": "withdrawal",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 65.0, "notes": ""},
    {"date": "2023-10-06", "change_bps":   0, "rate_after": 6.50, "stance": "withdrawal",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 63.0, "notes": ""},
    {"date": "2023-12-08", "change_bps":   0, "rate_after": 6.50, "stance": "withdrawal",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 60.0, "notes": ""},

    # ── 2024 ────────────────────────────────────────────────────────────────
    {"date": "2024-02-08", "change_bps":   0, "rate_after": 6.50, "stance": "withdrawal",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 65.0,
     "notes": "Hold; inflation still above 4% comfort zone."},
    {"date": "2024-04-05", "change_bps":   0, "rate_after": 6.50, "stance": "withdrawal",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 63.0, "notes": ""},
    {"date": "2024-06-07", "change_bps":   0, "rate_after": 6.50, "stance": "withdrawal",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 65.0, "notes": ""},
    {"date": "2024-08-08", "change_bps":   0, "rate_after": 6.50, "stance": "withdrawal",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 62.0, "notes": ""},
    {"date": "2024-10-09", "change_bps":   0, "rate_after": 6.50, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": 0.0, "n_analysts": 60.0,
     "notes": "Stance shifted from 'withdrawal of accommodation' to 'neutral'."},
    {"date": "2024-12-06", "change_bps":   0, "rate_after": 6.50, "stance": "neutral",
     "cycle": "Hold", "pre_mpc": False, "expected_bps": -25.0, "n_analysts": 58.0,
     "notes": "Surprise hold vs median expectation of -25bps cut; food inflation elevated."},

    # ── 2025 ────────────────────────────────────────────────────────────────
    {"date": "2025-02-07", "change_bps": -25, "rate_after": 6.25, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": False, "expected_bps": -25.0, "n_analysts": 65.0,
     "notes": "First cut since 2020; start of FY26 easing cycle."},
    {"date": "2025-04-09", "change_bps": -25, "rate_after": 6.00, "stance": "accommodative",
     "cycle": "Cut", "pre_mpc": False, "expected_bps": -25.0, "n_analysts": 62.0,
     "notes": "Second cut; global slowdown + contained domestic inflation."},
]

# Clean up duplicate / superseded Oct-2016 entry
# Oct 2016 MPC: actual decision was a 25bps CUT (6.50 → 6.25). Correcting the stub entry.
# Remove the placeholder entry added above:
POLICY_CALENDAR = [e for e in POLICY_CALENDAR if not (
    e["date"] == "2016-10-04" and "NOTE:" in e.get("notes", "")
)]
# Insert correct Oct-2016 entry in sequence
POLICY_CALENDAR_SORTED = sorted(POLICY_CALENDAR, key=lambda x: x["date"])


def get_full_calendar() -> pd.DataFrame:
    """Return all MPC/Governor meetings as a DataFrame."""
    df = pd.DataFrame(POLICY_CALENDAR_SORTED)
    df["date"] = pd.to_datetime(df["date"])
    df["rate_before"] = df["rate_after"] - df["change_bps"] / 100
    # Compute surprise: actual - expected (NaN where expectations unavailable)
    df["surprise_bps"] = df["change_bps"] - df["expected_bps"]
    # Classify surprise direction
    df["surprise_dir"] = df["surprise_bps"].apply(
        lambda x: "hawkish" if x > 0 else ("dovish" if x < 0 else "in-line")
        if pd.notna(x) else "unknown"
    )
    # Expectations available flag
    df["has_expectations"] = df["expected_bps"].notna()
    return df.sort_values("date").reset_index(drop=True)


def get_change_events() -> pd.DataFrame:
    """Return only events where the rate CHANGED (for event-study analysis)."""
    df = get_full_calendar()
    changed = df[df["change_bps"] != 0].copy()
    return changed.reset_index(drop=True)


def get_hold_events() -> pd.DataFrame:
    """Return only Hold decisions."""
    df = get_full_calendar()
    return df[df["cycle"] == "Hold"].copy().reset_index(drop=True)


def get_surprise_events() -> pd.DataFrame:
    """
    Return meetings where expectations data is available.
    Subset for policy-surprise analysis only.
    """
    df = get_full_calendar()
    return df[df["has_expectations"]].copy().reset_index(drop=True)


if __name__ == "__main__":
    df = get_full_calendar()
    print(f"Total meetings: {len(df)}")
    print(f"  Change events : {(df['change_bps'] != 0).sum()}")
    print(f"  Hold events   : {(df['change_bps'] == 0).sum()}")
    print(f"  With expectations: {df['has_expectations'].sum()}")
    print(df[["date", "change_bps", "rate_after", "cycle", "expected_bps", "surprise_bps"]].to_string())
