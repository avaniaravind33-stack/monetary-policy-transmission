"""
app.py — Monetary Policy Transmission & Indian Asset Markets
           A Goldman-Sachs GIR-style research dashboard

7-page Streamlit application. Launch with:
    cd /path/to/monetary-policy-transmission
    streamlit run dashboard/app.py
"""

import sys
import os
from pathlib import Path

# Allow imports from project root
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src.data_loader      import download_all, compute_returns, generate_synthetic_data
from src.rbi_events       import get_full_calendar
from src.event_study      import (
    run_event_study,
    run_rate_sensitivity,
    test_acar_significance,
    test_hike_vs_cut,
    correlate_surprise_vs_car,
)
from src.policy_surprise  import (
    build_surprise_table,
    merge_surprise_with_cars,
    regress_surprise_on_car,
    surprise_vs_inline_ttest,
    get_notable_surprise_events,
)
from src.statistical_tests import (
    test_acar_significance_all,
    test_hike_vs_cut_all,
    kruskal_wallis_regimes,
    regress_car_on_magnitude,
    build_summary_stats,
)
from src import visualizations as viz

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RBI Monetary Policy Transmission",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ── Main background ── */
.stApp { background-color: #0D1117; color: #E6EDF3; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #161B22;
    border-right: 1px solid #21262D;
}

/* ── Metric cards ── */
div[data-testid="metric-container"] {
    background-color: #161B22;
    border: 1px solid #21262D;
    border-radius: 8px;
    padding: 14px 20px;
}

/* ── Dataframes ── */
.dataframe { background-color: #161B22 !important; color: #E6EDF3 !important; }

/* ── Headers ── */
h1 { color: #F0F6FC; font-weight: 700; letter-spacing: -0.5px; }
h2 { color: #C9D1D9; font-weight: 600; }
h3 { color: #8B949E; font-weight: 500; }

/* ── Callout box ── */
.gs-callout {
    background: #161B22;
    border-left: 3px solid #58A6FF;
    border-radius: 4px;
    padding: 12px 18px;
    margin-bottom: 16px;
    font-size: 0.89rem;
    color: #C9D1D9;
    line-height: 1.6;
}

/* ── Warning box ── */
.gs-warn {
    background: #1A1200;
    border-left: 3px solid #F4A261;
    border-radius: 4px;
    padding: 10px 16px;
    margin-bottom: 14px;
    font-size: 0.85rem;
    color: #D29922;
}

/* ── Tabs ── */
button[data-baseweb="tab"] {
    background-color: #0D1117;
    color: #8B949E;
    border: none;
    font-size: 0.88rem;
    font-weight: 500;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #F0F6FC;
    border-bottom: 2px solid #58A6FF;
}
</style>
""", unsafe_allow_html=True)


# ─── Data Loading (cached) ───────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_data():
    """Load + cache all data for the session."""
    events = get_full_calendar()

    try:
        prices = download_all(force_refresh=False)
        synthetic = False
    except Exception:
        prices = generate_synthetic_data()
        synthetic = True

    returns = compute_returns(prices)

    result  = run_event_study(returns, events)
    ar_df   = result["ar_panel"]
    car_df  = result["car_panel"]
    ev_log  = result["event_log"]
    covered = result["covered_assets"]

    try:
        rate_sens = run_rate_sensitivity(returns, events)
    except Exception:
        rate_sens = pd.DataFrame()

    merged_surprise = merge_surprise_with_cars(car_df, events)

    return {
        "events":          events,
        "prices":          prices,
        "returns":         returns,
        "ar_df":           ar_df,
        "car_df":          car_df,
        "ev_log":          ev_log,
        "covered_assets":  covered,
        "rate_sensitivity":rate_sens,
        "merged_surprise": merged_surprise,
        "synthetic":       synthetic,
    }


with st.spinner("Loading RBI events, market data, and running event study…"):
    DATA = load_data()

events    = DATA["events"]
prices    = DATA["prices"]
returns   = DATA["returns"]
ar_df     = DATA["ar_df"]
car_df    = DATA["car_df"]
ev_log    = DATA["ev_log"]
covered   = DATA["covered_assets"]
rate_sens = DATA["rate_sensitivity"]
merged_s  = DATA["merged_surprise"]
SYNTHETIC = DATA["synthetic"]

ASSETS_CORE  = [a for a in ["Nifty50","BankNifty","GSec10Y","USDINR"] if a in covered]
ASSETS_BANKS = [a for a in ["HDFC_Bank","ICICI_Bank","SBI","Kotak_Bank"] if a in covered]
ASSETS_SEC   = [a for a in ["IT","Auto","FMCG","Pharma","Realty"] if a in covered]
ALL_ASSETS   = covered

HORIZON_COLS = [c for c in car_df.columns if c.startswith("CAR[")]


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Seal_of_the_Reserve_Bank_of_India.svg/200px-Seal_of_the_Reserve_Bank_of_India.svg.png",
             width=60)
    st.markdown("### Monetary Policy Transmission")
    st.markdown(
        '<p style="color:#8B949E;font-size:0.82rem;margin-top:-8px;">'
        'RBI Event Study · 2014–2025</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "📊 Executive Summary",
            "📅 Policy Timeline",
            "📈 Market Reaction",
            "🔬 Event Study",
            "⚡ Policy Surprise",
            "📐 Statistical Analysis",
            "📝 Research Conclusions",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    if SYNTHETIC:
        st.warning("⚠️ **Synthetic mode** — Yahoo Finance unavailable.\nResults are illustrative only.")
    else:
        st.success("✓ Live market data loaded")

    st.caption(f"Events in calendar: {len(events)}")
    st.caption(f"Assets: {len(covered)}")
    ok_events = ev_log[ev_log.get("status","") == "ok"] if "status" in ev_log.columns else ev_log
    st.caption(f"Events with clean estimation window: {len(ok_events)}")


# ─── PAGE HEADER helper ───────────────────────────────────────────────────────

def page_header(title: str, subtitle: str):
    st.markdown(f"# {title}")
    st.markdown(f'<p style="color:#8B949E;font-size:1.05rem;margin-top:-12px;">{subtitle}</p>',
                unsafe_allow_html=True)
    if SYNTHETIC:
        st.markdown(
            '<div class="gs-warn">⚠️ <strong>Synthetic data mode.</strong> '
            'Yahoo Finance is unavailable. Results are generated from a GBM simulation and '
            'are for display purposes only. Do not interpret as real market findings.</div>',
            unsafe_allow_html=True,
        )
    st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

if page == "📊 Executive Summary":
    page_header(
        "Monetary Policy Transmission — Indian Asset Markets",
        "How do RBI monetary-policy decisions propagate into equities, bonds, and the exchange rate?"
    )

    st.markdown(
        '<div class="gs-callout">'
        '<strong>Research question:</strong> After an RBI Monetary Policy Committee decision, '
        'do Indian equities (NIFTY 50, Bank NIFTY), government bond yields (10Y G-Sec), '
        'and the INR/USD exchange rate exhibit statistically abnormal returns? '
        'Is the market reaction larger when the policy decision is a <em>surprise</em>?'
        '</div>',
        unsafe_allow_html=True,
    )

    # KPI row
    n_total  = len(events)
    n_hikes  = len(events[events["cycle"] == "Hike"])
    n_cuts   = len(events[events["cycle"] == "Cut"])
    n_holds  = len(events[events["cycle"] == "Hold"])
    n_surps  = events["has_expectations"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("Total Policy Meetings", n_total)
    with c2: st.metric("Rate Hikes", n_hikes, delta="+ve ΔRate")
    with c3: st.metric("Rate Cuts",  n_cuts,  delta="-ve ΔRate")
    with c4: st.metric("Hold Decisions", n_holds)
    with c5: st.metric("Events with Market Expectations", n_surps, help="Reuters/Bloomberg poll data available")

    st.subheader("Policy Rate History")
    events["date"] = pd.to_datetime(events["date"])
    events_sorted = events.sort_values("date").copy()
    events_sorted["rate_before"] = events_sorted["rate_after"] - events_sorted["change_bps"] / 100
    fig_rate = viz.plot_rate_history(events_sorted)
    st.plotly_chart(fig_rate, use_container_width=True)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Methodology at a Glance")
        st.markdown("""
| Component | Detail |
|-----------|--------|
| Estimation window | [-120, -21] trading days |
| Event windows | [-1], [0], [0,+1], [0,+3], [0,+5] |
| Market model | OLS: r_asset = α + β·r_Nifty50 + ε |
| G-Sec treatment | First-difference of yield (Δy), constant-mean model |
| Surprise proxy | Actual − Expected (Reuters poll), where available |
| Statistical tests | t-tests, Welch, Kruskal-Wallis, OLS/HC3 |
""")

    with col2:
        st.subheader("Data Sources")
        st.markdown("""
| Asset | Source | Coverage |
|-------|---------|----------|
| NIFTY 50, Bank NIFTY | Yahoo Finance (^NSEI, ^NSEBANK) | 2013–2025 |
| 10Y G-Sec yield | Yahoo Finance (IN10YT=RR) | Partial |
| USD/INR | Yahoo Finance (USDINR=X) | 2013–2025 |
| Bank stocks | Yahoo Finance (.NS) | 2013–2025 |
| RBI rate decisions | RBI.org.in press releases | 2013–2025 |
| Market expectations | Reuters/Bloomberg polls | 2017+ only |
""")

    st.divider()
    st.markdown(
        '<div class="gs-warn">'
        '⚠️ <strong>Limitations:</strong> Sample sizes for cycle-specific tests are small '
        '(hikes N≈8–10, cuts N≈12–15). P-values should be treated as suggestive rather '
        'than definitive. Multiple testing is acknowledged; Bonferroni correction applied '
        'where noted. COVID emergency cuts (March–May 2020) may violate event independence. '
        'Expectations data is available only for meetings post-2017.'
        '</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — POLICY TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📅 Policy Timeline":
    page_header(
        "RBI Policy Timeline",
        "Complete record of monetary policy decisions — 2013 to 2025"
    )

    events["date"] = pd.to_datetime(events["date"])
    events_sorted = events.sort_values("date").copy()
    events_sorted["rate_before"] = events_sorted["rate_after"] - events_sorted["change_bps"] / 100

    tab1, tab2, tab3 = st.tabs(["Rate History", "Stance Evolution", "Full Event Table"])

    with tab1:
        st.markdown(
            '<div class="gs-callout">The repo rate fell from 8% in early 2014 to a record low of 4% '
            'during COVID easing (2020). An emergency hike was deployed in May 2022 (+40bps, '
            'off-cycle) as inflation spiked above the 6% upper band. Rate cuts resumed in early 2025.</div>',
            unsafe_allow_html=True,
        )
        fig_r = viz.plot_rate_history(events_sorted)
        st.plotly_chart(fig_r, use_container_width=True)

    with tab2:
        st.markdown(
            '<div class="gs-callout">The RBI\'s explicit stance signal (accommodative / neutral / '
            'withdrawal of accommodation / hawkish) has generally led rate moves. From mid-2022, '
            'the stance shifted to "withdrawal of accommodation" before actual hikes were delivered.</div>',
            unsafe_allow_html=True,
        )
        fig_stance = viz.plot_stance_timeline(events_sorted)
        st.plotly_chart(fig_stance, use_container_width=True)

    with tab3:
        fig_tbl = viz.plot_policy_calendar_table(events_sorted)
        st.plotly_chart(fig_tbl, use_container_width=True)

        with st.expander("View as DataFrame"):
            display_cols = ["date","change_bps","rate_after","stance","cycle","expected_bps","surprise_bps","pre_mpc","notes"]
            disp = events_sorted[[c for c in display_cols if c in events_sorted.columns]].copy()
            disp["date"] = disp["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(disp, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — MARKET REACTION
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📈 Market Reaction":
    page_header(
        "Market Reaction to RBI Decisions",
        "How do Indian asset prices behave on monetary-policy announcement days?"
    )

    if ar_df.empty:
        st.error("Event study data not available — check data loading.")
        st.stop()

    # Controls
    col1, col2, col3 = st.columns(3)
    with col1:
        cycle_filt = st.selectbox("Cycle filter", ["All","Hike","Cut","Hold"])
    with col2:
        rel_day = st.selectbox("Event day (relative)", [-1, 0, 1, 3, 5], index=1)
    with col3:
        asset_group = st.selectbox("Asset group", ["Core (4)", "Banks (4)", "Sectors (5)", "All"])

    group_map = {
        "Core (4)":    ASSETS_CORE,
        "Banks (4)":   ASSETS_BANKS,
        "Sectors (5)": ASSETS_SEC,
        "All":         ALL_ASSETS,
    }
    show_assets = group_map[asset_group]

    st.subheader(f"Mean Abnormal Return — Day {rel_day:+d}")
    fig_bar = viz.plot_asset_event_day_bars(ar_df, show_assets, rel_day, cycle_filt)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown(
        '<div class="gs-warn">Mean AR across all events. Small N per cycle '
        '(hike≈8, cut≈12) means large standard errors — treat bars as indicative, '
        'not definitive. See Statistical Analysis tab for significance tests.</div>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader("Price Path Around a Specific RBI Event")

    change_events = events[events["change_bps"] != 0].sort_values("date", ascending=False)
    event_options = (
        change_events["date"].dt.strftime("%Y-%m-%d") + " | " +
        change_events["cycle"].astype(str) + " " +
        change_events["change_bps"].astype(str) + "bps"
    )
    selected_ev_str = st.selectbox("Select an event", event_options.values)
    selected_date   = pd.to_datetime(selected_ev_str.split(" | ")[0])

    ev_assets = st.multiselect(
        "Plot assets", ALL_ASSETS,
        default=[a for a in ["Nifty50","BankNifty","USDINR"] if a in ALL_ASSETS],
    )

    if ev_assets:
        fig_path = viz.plot_asset_price_around_event(prices, selected_date, ev_assets, window_days=10)
        st.plotly_chart(fig_path, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 4 — EVENT STUDY
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "🔬 Event Study":
    page_header(
        "Event Study — Abnormal Returns",
        "Does the market show statistically abnormal returns around RBI meetings?"
    )

    if car_df.empty:
        st.error("CAR panel empty — no events were processed.")
        st.stop()

    tab_heatmap, tab_fan, tab_asym, tab_data = st.tabs([
        "ACAR Heatmap", "CAR Fan Chart", "Hike vs Cut", "Raw Data"
    ])

    with tab_heatmap:
        cycle_h = st.selectbox("Cycle", ["All","Hike","Cut","Hold"], key="hm_cycle")
        st.markdown(
            '<div class="gs-callout">Average Cumulative Abnormal Return (%) by asset × event window. '
            'Blue/green tones indicate negative ACAR; red indicates positive. '
            'Significance tests are in the Statistical Analysis tab.</div>',
            unsafe_allow_html=True,
        )
        fig_hm = viz.plot_acar_heatmap(car_df, cycle_h)
        st.plotly_chart(fig_hm, use_container_width=True)

    with tab_fan:
        col1, col2 = st.columns(2)
        with col1:
            fan_asset = st.selectbox("Asset", ALL_ASSETS, key="fan_asset")
        with col2:
            fan_cycle = st.selectbox("Cycle", ["All","Hike","Cut","Hold"], key="fan_cycle")

        st.markdown(
            '<div class="gs-callout">Fan chart shows mean CAR (solid line) '
            '± 1 standard deviation (shaded band) over the event window. '
            'A flat post-announcement line would suggest price discovery is rapid and complete.</div>',
            unsafe_allow_html=True,
        )
        fig_fan = viz.plot_car_fan(ar_df, fan_asset, fan_cycle)
        st.plotly_chart(fig_fan, use_container_width=True)

    with tab_asym:
        col1, col2 = st.columns(2)
        with col1:
            asym_asset   = st.selectbox("Asset",   ALL_ASSETS,   key="asym_asset")
        with col2:
            asym_horizon = st.selectbox("Horizon", HORIZON_COLS, key="asym_hz")

        st.markdown(
            '<div class="gs-callout">Box plots of individual-event CAR by rate cycle. '
            'An asymmetric pattern (hike CARs ≠ cut CARs in magnitude) would suggest '
            'non-linear transmission.</div>',
            unsafe_allow_html=True,
        )
        fig_asym = viz.plot_hike_cut_comparison(car_df, asym_asset, asym_horizon)
        st.plotly_chart(fig_asym, use_container_width=True)

        # Quick stats
        hvc = test_hike_vs_cut(car_df, asym_asset, asym_horizon)
        if "t_stat_welch" in hvc:
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("N (Hike)", hvc.get("n_hike"))
            with c2: st.metric("N (Cut)",  hvc.get("n_cut"))
            with c3: st.metric("Welch t",  f"{hvc.get('t_stat_welch',np.nan):.3f}")
            with c4:
                p = hvc.get("p_value", 1.0)
                stars = "**" if p < 0.01 else ("*" if p < 0.05 else ("· " if p < 0.10 else "n.s."))
                st.metric("p-value", f"{p:.4f}", delta=stars, delta_color="off")
        else:
            st.info(hvc.get("note",""))

    with tab_data:
        st.download_button(
            "⬇ Download CAR Panel (CSV)",
            data=car_df.to_csv(index=False),
            file_name="car_panel.csv",
            mime="text/csv",
        )
        n_show = st.slider("Rows to show", 20, 200, 50)
        st.dataframe(car_df.head(n_show), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 5 — POLICY SURPRISE
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "⚡ Policy Surprise":
    page_header(
        "Policy Surprise Analysis",
        "Does a larger-than-expected rate change drive a larger market reaction?"
    )

    st.markdown(
        '<div class="gs-callout">'
        '<strong>Surprise</strong> = Actual change − Expected change (Reuters poll median). '
        'A positive surprise is hawkish (more tightening than forecast). '
        'Expectations data is available for MPC-era meetings (2017+) only; '
        'pre-MPC surprise values are coded as NaN and excluded from all regressions.</div>',
        unsafe_allow_html=True,
    )

    surprise_tbl = build_surprise_table(events)
    notable      = get_notable_surprise_events(events, threshold_bps=25.0)

    if surprise_tbl.empty:
        st.warning("No expectations data found in event calendar. Cannot run surprise analysis.")
        st.stop()

    tab_bar, tab_scatter, tab_reg, tab_notable = st.tabs([
        "Surprise Bar", "Scatter Plot", "Regression", "Notable Events"
    ])

    with tab_bar:
        fig_sb = viz.plot_surprise_bar(surprise_tbl)
        st.plotly_chart(fig_sb, use_container_width=True)

        st.caption(
            f"N = {len(surprise_tbl)} meetings with consensus forecasts. "
            "Source: Reuters poll medians, Bloomberg survey (cross-referenced)"
        )

    with tab_scatter:
        col1, col2 = st.columns(2)
        with col1:
            sc_asset   = st.selectbox("Asset",   ASSETS_CORE + ASSETS_BANKS, key="sc_asset")
        with col2:
            sc_horizon = st.selectbox("Horizon", HORIZON_COLS, key="sc_hz")

        if merged_s.empty:
            st.warning("No merged surprise + CAR data available.")
        else:
            fig_sc = viz.plot_surprise_scatter(merged_s, sc_asset, sc_horizon)
            st.plotly_chart(fig_sc, use_container_width=True)

    with tab_reg:
        reg_asset   = st.selectbox("Asset",   ASSETS_CORE, key="reg_asset")
        reg_horizon = st.selectbox("Horizon", HORIZON_COLS, key="reg_hz")

        if not merged_s.empty:
            res = regress_surprise_on_car(merged_s, reg_asset, reg_horizon)
            note = res.get("note", "")
            if note:
                st.info(f"Note: {note}")
            else:
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("N", res["n"])
                with c2: st.metric("γ₁ (surprise coeff)", f"{res['gamma1']:.5f}")
                with c3: st.metric("t-stat (γ₁)", f"{res['t_gamma1']:.3f}")
                with c4:
                    p = res["p_gamma1"]
                    stars = "*" if p < 0.05 else "n.s."
                    st.metric("p-value (γ₁)", f"{p:.4f}", delta=stars, delta_color="off")
                st.metric("R²", f"{res['r_squared']:.4f}")

                col_a, col_b = st.columns(2)
                with col_a:
                    # Surprise vs in-line
                    ttest = surprise_vs_inline_ttest(merged_s, reg_asset, reg_horizon)
                    if "t_stat_welch" in ttest:
                        st.markdown("**Surprise vs In-Line Events**")
                        st.json({k: round(v, 4) if isinstance(v, float) else v
                                 for k, v in ttest.items()})
                with col_b:
                    st.markdown("**Regression:** `CAR = γ₀ + γ₁ · Surprise_bps + ε`")
                    st.markdown("HC3 White-corrected standard errors")
                    st.markdown(
                        '<div class="gs-warn">⚠️ Small N for surprise subsample '
                        '(N ≤ 25). Regression coefficients are suggestive. '
                        'Interpret alongside economic priors.</div>',
                        unsafe_allow_html=True,
                    )

    with tab_notable:
        st.markdown("### High-Surprise Events — |Surprise| ≥ 25 bps")
        if notable.empty:
            st.info("No events exceed the 25bps surprise threshold in the available data.")
        else:
            disp_cols = [c for c in ["date","cycle","change_bps","expected_bps","surprise_bps","notes"] if c in notable.columns]
            notable2  = notable[disp_cols].copy()
            if "date" in notable2.columns:
                notable2["date"] = pd.to_datetime(notable2["date"]).dt.strftime("%Y-%m-%d")
            st.dataframe(notable2, use_container_width=True, hide_index=True)

            st.markdown(
                '<div class="gs-callout">'
                'These are the analytically most interesting events where the RBI meaningfully '
                'deviated from consensus expectations. They are the strongest tests of the '
                'policy surprise → market reaction hypothesis.</div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 6 — STATISTICAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📐 Statistical Analysis":
    page_header(
        "Statistical Analysis",
        "Formal hypothesis tests on abnormal returns — with explicit limitations"
    )

    st.markdown(
        '<div class="gs-warn">'
        '⚠️ <strong>Multiple testing notice:</strong> We run many tests across assets, '
        'horizons, and cycles. At α=0.05, we expect false positives by chance. '
        'Bonferroni-corrected threshold for ~30 tests: α* ≈ 0.0017. '
        'Stars indicate uncorrected significance; interpret accordingly.</div>',
        unsafe_allow_html=True,
    )

    tab_acar, tab_hvc, tab_kw, tab_mag, tab_sens = st.tabs([
        "ACAR Significance", "Hike vs Cut", "Kruskal-Wallis", "Magnitude Effect", "Rate Sensitivity"
    ])

    with tab_acar:
        st.markdown("#### H₀: ACAR = 0 — One-sample t-test")
        st.markdown(
            "Tests whether average cumulative abnormal returns across all events are "
            "significantly different from zero."
        )
        cycle_a = st.selectbox("Cycle subset", ["All","Hike","Cut","Hold"], key="acar_c")
        hz_a    = st.selectbox("Horizon", HORIZON_COLS, key="acar_hz")

        acar_all = test_acar_significance_all(
            car_df, ALL_ASSETS, HORIZON_COLS,
            cycles=[None if cycle_a == "All" else cycle_a],
        )
        acar_show = acar_all[acar_all["horizon"] == hz_a].sort_values("p_value")

        if not acar_show.empty:
            fig_pval = viz.plot_stat_test_results(
                acar_all,
                title=f"ACAR Significance — p-values by Asset × Horizon ({cycle_a} events)"
            )
            st.plotly_chart(fig_pval, use_container_width=True)

            acar_fmt = acar_show.copy()
            for col in ["mean_car","std_car"]:
                if col in acar_fmt.columns:
                    acar_fmt[col] = (acar_fmt[col] * 100).round(4).astype(str) + "%"
            for col in ["t_stat","p_value"]:
                if col in acar_fmt.columns:
                    acar_fmt[col] = acar_fmt[col].round(4)
            st.dataframe(acar_fmt, use_container_width=True, hide_index=True)

    with tab_hvc:
        st.markdown("#### H₀: Mean CAR(Hike) = Mean CAR(Cut) — Welch two-sample t-test")
        hvc_all = test_hike_vs_cut_all(car_df, ALL_ASSETS, HORIZON_COLS)
        hz_h    = st.selectbox("Horizon", HORIZON_COLS, key="hvc_hz")
        hvc_show = hvc_all[hvc_all["horizon"] == hz_h].sort_values("p_value")
        hvc_fmt  = hvc_show.copy()
        for col in ["mean_hike","mean_cut"]:
            if col in hvc_fmt.columns:
                hvc_fmt[col] = (hvc_fmt[col] * 100).round(4).astype(str) + "%"
        for col in ["t_stat_welch","p_value"]:
            if col in hvc_fmt.columns:
                hvc_fmt[col] = hvc_fmt[col].round(4)
        st.dataframe(hvc_fmt, use_container_width=True, hide_index=True)
        st.caption("Welch variant used (unequal sample size and variance). Small N — interpret cautiously.")

    with tab_kw:
        st.markdown("#### Kruskal-Wallis — Non-parametric robustness check")
        st.markdown(
            "H₀: CAR distribution is identical across Hike / Cut / Hold regimes. "
            "Used as a robustness check for the two-sample t-test when normality is questionable (N<10 per group)."
        )
        hz_kw       = st.selectbox("Horizon",     HORIZON_COLS, key="kw_hz")
        exc_covid   = st.checkbox("Exclude March–May 2020 COVID emergency cuts", value=True,
                                  help="These events occurred in quick succession and may share market conditions")

        kw_results = kruskal_wallis_regimes(car_df, ALL_ASSETS, hz_kw, exclude_covid=exc_covid)
        kw_fmt = kw_results.copy()
        for col in ["H_stat","p_value"]:
            if col in kw_fmt.columns:
                kw_fmt[col] = kw_fmt[col].round(4)
        st.dataframe(kw_fmt, use_container_width=True, hide_index=True)

    with tab_mag:
        st.markdown("#### Magnitude Regression — OLS: |CAR| ~ β₀ + β₁·|ΔRate|")
        st.markdown(
            "H₀: β₁ = 0. Tests whether larger rate changes produce larger (in absolute value) market reactions."
        )
        mag_asset = st.selectbox("Asset",   ALL_ASSETS,   key="mag_asset")
        mag_hz    = st.selectbox("Horizon", HORIZON_COLS, key="mag_hz")

        mag_result = regress_car_on_magnitude(car_df, mag_asset, mag_hz)
        if "note" in mag_result:
            st.info(mag_result["note"])
        else:
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: st.metric("N", mag_result["n"])
            with c2: st.metric("β₁", f"{mag_result['beta1']:.5f}")
            with c3: st.metric("t (β₁)", f"{mag_result['t_beta1']:.3f}")
            with c4:
                p = mag_result["p_beta1"]
                st.metric("p(β₁)", f"{p:.4f}", delta="*" if p < 0.05 else "n.s.", delta_color="off")
            with c5: st.metric("R²", f"{mag_result['r_squared']:.4f}")
            st.info(mag_result["interpretation"])

    with tab_sens:
        st.markdown("#### Rate Sensitivity (β₂) — HAC-corrected full-sample regression")
        st.markdown(
            "Model: `r_asset = α + β₁·r_market + β₂·RateChange_bps + ε`  \n"
            "Newey-West HAC standard errors (maxlags=5). Estimated over full 2013–2025 sample."
        )
        if rate_sens.empty:
            st.warning("Rate sensitivity data not available.")
        else:
            fig_rs = viz.plot_rate_sensitivity(rate_sens)
            st.plotly_chart(fig_rs, use_container_width=True)
            with st.expander("Full regression table"):
                rs_fmt = rate_sens.copy().reset_index()
                for col in ["beta_rate"]:
                    if col in rs_fmt.columns:
                        rs_fmt[col] = (rs_fmt[col] * 100).round(4)
                for col in ["t_beta_rate","p_beta_rate","r_squared"]:
                    if col in rs_fmt.columns:
                        rs_fmt[col] = rs_fmt[col].round(4)
                st.dataframe(rs_fmt, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 7 — RESEARCH CONCLUSIONS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📝 Research Conclusions":
    page_header(
        "Research Conclusions",
        "What does the evidence say about monetary policy transmission in India?"
    )

    st.markdown(
        '<div class="gs-warn">'
        '⚠️ <strong>Caveats apply throughout.</strong> Sample sizes are small; '
        'p-values should be interpreted with caution. The results below describe '
        'patterns in the data — they are not causal claims unless otherwise noted.</div>',
        unsafe_allow_html=True,
    )

    st.subheader("Headline Chart — Policy Transmission by Asset Class")
    if not car_df.empty:
        fig_tx = viz.plot_transmission_summary(car_df)
        st.plotly_chart(fig_tx, use_container_width=True)

    st.divider()
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Key Findings (subject to limitations)")
        st.markdown("""
**1. Equity Transmission**
- NIFTY 50 and Bank NIFTY show negative Day-0 ARs on hike days and
  positive ARs on cut days — directionally consistent with theory.
- Bank NIFTY tends to show larger absolute ARs than NIFTY 50,
  consistent with banking sector's higher rate exposure.
- Statistical significance is limited at α=0.05 after Bonferroni correction.

**2. G-Sec Yield Transmission**
- 10Y G-Sec yields typically rise (positive Δy AR) on hike days and
  fall on cut days — again directionally consistent.
- Data coverage for IN10YT=RR is incomplete pre-2017; results should
  be treated as preliminary.

**3. FX Transmission**
- USD/INR responses are economically small on most event days.
  This is consistent with the RBI's active FX intervention policy
  which tends to dampen exchange-rate volatility around policy decisions.

**4. Policy Surprise Effect**
- For the subsample of meetings with expectations data (N ≤ 25),
  there is a directionally consistent positive relationship between
  hawkish surprise and negative equity ARs.
- The γ₁ coefficient from surprise regression is generally not
  significant at 5% level — unsurprising given the very small N.

**5. Rate Sensitivity Cross-Section**
- Realty and Banking sectors show the highest β₂ (rate sensitivity),
  consistent with their balance-sheet exposure to borrowing costs.
- IT and FMCG show lower β₂, consistent with lower leverage and
  defensive revenue profiles.
""")

    with col_r:
        st.subheader("What the Evidence Does NOT Show")
        st.markdown("""
This analysis **cannot** credibly claim:

- Precise point estimates of transmission coefficients
  (sample sizes are too small for precise estimation)
- Causal identification — rate changes are endogenous to
  the macro environment; we cannot rule out confounders
- Structural stability — the relationship between policy
  surprises and market reactions may differ across periods
  (pre-MPC vs MPC, low-inflation vs high-inflation regimes)
- Prediction — past market reactions to rate changes do not
  reliably forecast future ones

**These results should be read as descriptive evidence
consistent with standard monetary-transmission theory,
not as proof of that theory.**
""")

        st.markdown('<div class="gs-callout">📎 Full methodology documented in <code>research_report/monetary_policy_transmission.md</code></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("Suggested Further Work")
    st.markdown("""
| Extension | Rationale |
|-----------|-----------|
| High-frequency intraday data (5-min returns) | Cleanly isolates the announcement effect from intraday noise |
| Structural break tests (pre/post MPC, COVID) | Tests whether transmission changed with MPC formation in Oct 2016 |
| Ordered probit on stance → rate change | Models the ordinal stance variable to predict direction of next move |
| Factor-model extensions (Fama-French India) | Controls for size/value exposure in cross-section of sensitivity |
| Longer surprise series via inflation linking | Can proxy pre-2017 expectations via OIS-repo rate spread |
| VAR with sign restrictions | Isolates demand vs supply components of monetary-policy shocks |
""")

    # Download buttons
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if not car_df.empty:
            st.download_button("⬇ CAR Panel (CSV)", data=car_df.to_csv(index=False),
                               file_name="car_panel.csv", mime="text/csv")
    with col2:
        if not ar_df.empty:
            st.download_button("⬇ AR Panel (CSV)", data=ar_df.to_csv(index=False),
                               file_name="ar_panel.csv", mime="text/csv")
    with col3:
        events_exp = events.copy()
        events_exp["date"] = events_exp["date"].dt.strftime("%Y-%m-%d")
        st.download_button("⬇ RBI Event Calendar (CSV)", data=events_exp.to_csv(index=False),
                           file_name="rbi_events.csv", mime="text/csv")
