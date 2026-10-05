"""
visualizations.py — All Plotly charts for the Monetary Policy Transmission dashboard.

Design principles:
  - Every chart answers a specific research question (stated in the chart title).
  - Dark research-grade color palette; no decorative elements.
  - Source attribution beneath each chart.
  - No fabricated conclusions in chart text.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Color system ──────────────────────────────────────────────────────────────
HIKE  = "#E63946"   # red   → tightening
CUT   = "#2A9D8F"   # teal  → easing
HOLD  = "#6B7280"   # grey  → unchanged
SURP  = "#F4A261"   # amber → surprise

ASSET_COLORS = {
    "Nifty50":    "#F0F6FC",
    "BankNifty":  "#E63946",
    "GSec10Y":    "#457B9D",
    "USDINR":     "#F4A261",
    "HDFC_Bank":  "#8338EC",
    "ICICI_Bank": "#2A9D8F",
    "SBI":        "#FB8500",
    "Kotak_Bank": "#FF006E",
    "IT":         "#38B000",
    "Auto":       "#E9C46A",
    "FMCG":       "#264653",
    "Pharma":     "#A8DADC",
    "Realty":     "#FF6B6B",
}

BG    = "#0D1117"
PANEL = "#161B22"
GRID  = "#21262D"
TEXT  = "#E6EDF3"
MUTED = "#8B949E"

_BASE = dict(
    plot_bgcolor  = BG,
    paper_bgcolor = BG,
    font          = dict(color=TEXT, family="Inter, -apple-system, sans-serif", size=12),
    margin        = dict(l=60, r=40, t=70, b=55),
    xaxis         = dict(gridcolor=GRID, zeroline=False, linecolor=GRID),
    yaxis         = dict(gridcolor=GRID, zeroline=False, linecolor=GRID),
    legend        = dict(
        bgcolor="#1C2128", bordercolor=GRID, borderwidth=1,
        font=dict(size=11), orientation="v",
    ),
)

def _base(fig, **overrides):
    kw = {**_BASE, **overrides}
    fig.update_layout(**kw)
    return fig

SOURCE_NOTE = "Source: Yahoo Finance / NSE. RBI rates: RBI.org.in press releases."


# ─── PAGE 1: Executive Summary ───────────────────────────────────────────────

def plot_rate_history(events_df: pd.DataFrame) -> go.Figure:
    """
    RQ: What is the path of RBI monetary policy and its macro context?
    Shows repo rate step-chart with cycle annotations.
    """
    df = events_df.sort_values("date").copy()
    # Build step-function coordinates
    rate_x, rate_y = [], []
    for _, ev in df.iterrows():
        rate_x += [ev["date"], ev["date"]]
        rate_y  += [ev["rate_before"], ev["rate_after"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rate_x, y=rate_y,
        mode="lines",
        line=dict(color="#F0F6FC", width=2.5),
        name="Repo Rate (%)",
    ))

    # Event markers
    for _, ev in df[df["change_bps"] != 0].iterrows():
        color = HIKE if ev["cycle"] == "Hike" else CUT
        fig.add_scatter(
            x=[ev["date"]], y=[ev["rate_after"]],
            mode="markers",
            marker=dict(color=color, size=8, symbol="circle"),
            name=ev["cycle"],
            showlegend=False,
        )
        if abs(ev["change_bps"]) >= 40:
            sign = "+" if ev["change_bps"] > 0 else ""
            fig.add_annotation(
                x=ev["date"], y=ev["rate_after"] + 0.08,
                text=f"{sign}{int(ev['change_bps'])}bp",
                showarrow=False,
                font=dict(size=9, color=color),
            )

    # Shade rate cycles
    cycle_periods = [
        ("2015-01-15", "2016-04-05", CUT,  "Easing 2015-16"),
        ("2018-06-06", "2023-02-08", HIKE, "Tightening 2018 + 2022-23"),
        ("2019-02-07", "2020-05-22", CUT,  "Easing 2019-20"),
        ("2025-02-07", "2025-04-09", CUT,  "Easing 2025"),
    ]
    for start, end, col, label in cycle_periods:
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor=col, opacity=0.07, layer="below",
            line_width=0, annotation_text=None,
        )

    _base(fig,
          title=dict(text="RBI Repo Rate — Policy Cycle History (2014–2025)", font=dict(size=17)),
          xaxis_title="Date",
          yaxis_title="Repo Rate (%)",
          yaxis=dict(gridcolor=GRID, zeroline=False, ticksuffix="%"),
          annotations=[dict(
              x=0.01, y=-0.10, xref="paper", yref="paper",
              text=SOURCE_NOTE, showarrow=False,
              font=dict(size=10, color=MUTED), align="left",
          )],
    )
    return fig


# ─── PAGE 2: Policy Timeline ──────────────────────────────────────────────────

def plot_policy_calendar_table(events_df: pd.DataFrame) -> go.Figure:
    """Interactive policy event table as a Plotly Figure for embed consistency."""
    df    = events_df.sort_values("date", ascending=False).copy()
    df["date_str"]    = df["date"].dt.strftime("%Y-%m-%d")
    df["change_str"]  = df["change_bps"].apply(lambda x: f"+{x}" if x > 0 else (str(x) if x != 0 else "Hold"))
    df["rate_str"]    = df["rate_after"].apply(lambda x: f"{x:.2f}%")
    df["exp_str"]     = df["expected_bps"].apply(
        lambda x: f"{'+' if x > 0 else ''}{x:.0f}" if pd.notna(x) else "N/A"
    )
    df["surp_str"]    = df["surprise_bps"].apply(
        lambda x: f"{'+' if x > 0 else ''}{x:.0f}" if pd.notna(x) else "N/A"
    )

    colors = []
    for _, row in df.iterrows():
        if row["cycle"] == "Hike":  colors.append("#7B1D1D")
        elif row["cycle"] == "Cut": colors.append("#14532D")
        else:                       colors.append(PANEL)

    fig = go.Figure(go.Table(
        header=dict(
            values=["Date","Change (bps)","Rate After","Stance","Exp'd (bps)","Surprise","Cycle"],
            fill_color="#1C2128",
            font=dict(color=TEXT, size=12),
            align="center", height=36,
        ),
        cells=dict(
            values=[
                df["date_str"], df["change_str"], df["rate_str"],
                df["stance"],   df["exp_str"],    df["surp_str"], df["cycle"],
            ],
            fill_color=[[colors[i] for i in range(len(df))]],
            font=dict(color=TEXT, size=11),
            align="center", height=30,
        ),
    ))
    _base(fig, title=dict(text="RBI Monetary Policy Calendar — Full Record", font=dict(size=16)),
          margin=dict(l=20, r=20, t=60, b=40))
    return fig


def plot_stance_timeline(events_df: pd.DataFrame) -> go.Figure:
    """
    RQ: How has the RBI's stated policy stance evolved over time?
    """
    STANCE_NUM = {
        "hawkish":       3,
        "withdrawal":    2,
        "neutral":       1,
        "accommodative": 0,
    }
    STANCE_LABELS = {0:"Accommodative", 1:"Neutral", 2:"Withdrawal", 3:"Hawkish"}
    STANCE_COLORS = {
        "hawkish":       HIKE,
        "withdrawal":    "#F77F00",
        "neutral":       HOLD,
        "accommodative": CUT,
    }

    df = events_df.sort_values("date").copy()
    df["stance_num"] = df["stance"].map(STANCE_NUM).fillna(1)

    fig = go.Figure()
    for stance, num in STANCE_NUM.items():
        mask = df["stance"] == stance
        fig.add_trace(go.Scatter(
            x=df[mask]["date"], y=df[mask]["stance_num"],
            mode="markers",
            marker=dict(
                color=STANCE_COLORS.get(stance, HOLD),
                size=10, symbol="square",
            ),
            name=STANCE_LABELS.get(num, stance.title()),
        ))

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["stance_num"],
        mode="lines",
        line=dict(color=GRID, width=1, dash="dot"),
        showlegend=False,
    ))

    _base(fig,
          title=dict(text="RBI Policy Stance Evolution — Has the Stance Predicted Future Moves?", font=dict(size=16)),
          xaxis_title="Date",
          yaxis=dict(
              tickvals=[0,1,2,3],
              ticktext=["Accommodative","Neutral","Withdrawal","Hawkish"],
              gridcolor=GRID, zeroline=False,
          ),
          annotations=[dict(
              x=0.01, y=-0.12, xref="paper", yref="paper",
              text=SOURCE_NOTE, showarrow=False,
              font=dict(size=10, color=MUTED), align="left",
          )],
    )
    return fig


# ─── PAGE 3: Market Reaction ──────────────────────────────────────────────────

def plot_asset_event_day_bars(
    ar_df: pd.DataFrame,
    assets: list[str],
    rel_day: int = 0,
    cycle_filter: str = "All",
) -> go.Figure:
    """
    RQ: Which asset class reacts most strongly on RBI announcement days?
    Bar chart: mean AR on Day 0 by asset, split by cycle.
    """
    sub = ar_df[ar_df["rel_day"] == rel_day].copy()
    if cycle_filter != "All":
        sub = sub[sub["cycle"] == cycle_filter]

    means = sub.groupby("asset")["ar"].mean().reset_index()
    means = means[means["asset"].isin(assets)].sort_values("ar")
    means["ar_pct"] = means["ar"] * 100

    colors = [ASSET_COLORS.get(a, HOLD) for a in means["asset"]]

    fig = go.Figure(go.Bar(
        x=means["asset"], y=means["ar_pct"],
        marker_color=colors,
        text=[f"{v:.3f}%" for v in means["ar_pct"]],
        textposition="outside",
    ))

    _base(fig,
          title=dict(
              text=f"Mean Abnormal Return on Event Day (Day {rel_day:+d}) — {cycle_filter} Events",
              font=dict(size=16)
          ),
          xaxis_title="Asset",
          yaxis=dict(gridcolor=GRID, zeroline=True, zerolinecolor=MUTED, ticksuffix="%"),
          showlegend=False,
          annotations=[dict(
              x=0.01, y=-0.14, xref="paper", yref="paper",
              text=SOURCE_NOTE, showarrow=False,
              font=dict(size=10, color=MUTED), align="left",
          )],
    )
    return fig


def plot_asset_price_around_event(
    prices: pd.DataFrame,
    event_date: pd.Timestamp,
    assets: list[str],
    window_days: int = 10,
) -> go.Figure:
    """
    RQ: What happened to asset prices in the days surrounding a specific event?
    Shows indexed (= 100 on t-1) price path for each asset.
    """
    idx = prices.index
    try:
        t0_loc = idx.get_loc(event_date)
    except KeyError:
        for lag in range(1, 6):
            d = event_date + pd.Timedelta(days=lag)
            if d in idx:
                t0_loc = idx.get_loc(d)
                break
        else:
            return go.Figure().update_layout(title="Event date not found", **_BASE)

    start = max(0, t0_loc - window_days)
    end   = min(len(idx) - 1, t0_loc + window_days)

    slug = prices.iloc[start:end + 1]
    base = slug.iloc[window_days]   # t=0 as base

    fig = go.Figure()
    for asset in assets:
        if asset not in slug.columns:
            continue
        indexed = slug[asset] / base[asset] * 100
        fig.add_trace(go.Scatter(
            x=list(range(-window_days, len(indexed) - window_days)),
            y=indexed.values,
            mode="lines+markers",
            marker=dict(size=4),
            line=dict(color=ASSET_COLORS.get(asset, HOLD), width=2),
            name=asset,
        ))

    fig.add_vline(x=0, line=dict(color="#F0F6FC", dash="dash", width=1.5))
    fig.add_hline(y=100, line=dict(color=MUTED, width=0.8, dash="dot"))
    _base(fig,
          title=dict(
              text=f"Asset Prices ±{window_days} Days Around {event_date.date()} RBI Decision (Indexed=100)",
              font=dict(size=16),
          ),
          xaxis_title="Trading Days from Announcement",
          yaxis=dict(gridcolor=GRID, zeroline=False),
    )
    return fig


# ─── PAGE 4: Event Study ─────────────────────────────────────────────────────

def plot_acar_heatmap(car_df: pd.DataFrame, cycle_filter: str = "All") -> go.Figure:
    """
    RQ: Which assets show persistently abnormal returns across event horizons?
    Heatmap: ACAR (%) by asset × event window.
    """
    sub = car_df if cycle_filter == "All" else car_df[car_df["cycle"] == cycle_filter]
    horizon_cols = [c for c in car_df.columns if c.startswith("CAR[")]

    assets   = sub["asset"].unique()
    matrix   = []
    for asset in assets:
        row = sub[sub["asset"] == asset][horizon_cols].mean()
        matrix.append(row.values * 100)

    z    = np.array(matrix)
    text = [[f"{v:.2f}%" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z    = z,
        x    = [h.replace("CAR","").replace("[","[") for h in horizon_cols],
        y    = list(assets),
        text = text, texttemplate="%{text}",
        colorscale=[
            [0.00, "#1B4332"], [0.35, "#2D6A4F"],
            [0.50, BG],
            [0.65, "#7B1D1D"], [1.00, HIKE],
        ],
        zmid=0,
        colorbar=dict(
            title=dict(text="ACAR (%)", font=dict(color=TEXT)),
            tickfont=dict(color=TEXT),
        ),
    ))
    suffix = "" if cycle_filter == "All" else f" — {cycle_filter} Cycle"
    _base(fig,
          title=dict(
              text=f"Average CAR by Asset & Event Window{suffix} — Do Reactions Persist?",
              font=dict(size=16),
          ),
          annotations=[dict(
              x=0.01, y=-0.14, xref="paper", yref="paper",
              text=SOURCE_NOTE, showarrow=False,
              font=dict(size=10, color=MUTED), align="left",
          )],
    )
    return fig


def plot_car_fan(
    ar_df: pd.DataFrame,
    asset: str,
    cycle_filter: str = "All",
) -> go.Figure:
    """
    RQ: Does the market reaction build up or reverse over the days following an RBI decision?
    Fan chart: mean ± 1σ cumulative AR over the event window.
    """
    sub = ar_df[ar_df["asset"] == asset].copy()
    if cycle_filter != "All":
        sub = sub[sub["cycle"] == cycle_filter]

    # For each event, compute cumulative AR across sorted rel_days
    cum_records = []
    for ev_date, grp in sub.groupby("event_date"):
        grp = grp.sort_values("rel_day")
        cum = 0.0
        for _, row in grp.iterrows():
            ar_val = row["ar"]
            if pd.notna(ar_val):
                cum += ar_val
            cum_records.append({"event_date": ev_date, "rel_day": row["rel_day"], "cum_ar": cum})

    if not cum_records:
        return go.Figure().update_layout(title=f"No data for {asset}", **_BASE)

    panel = pd.DataFrame(cum_records)
    stats = panel.groupby("rel_day")["cum_ar"].agg(["mean","std","count"]).reset_index()
    stats.columns = ["rel_day","mean","std","n"]

    color = ASSET_COLORS.get(asset, "#58A6FF")
    hex_alpha = color + "30"

    fig = go.Figure()
    # ±1σ band
    fig.add_trace(go.Scatter(
        x=list(stats["rel_day"]) + list(stats["rel_day"])[::-1],
        y=list((stats["mean"] + stats["std"]) * 100) + list((stats["mean"] - stats["std"]) * 100)[::-1],
        fill="toself", fillcolor=hex_alpha,
        line=dict(width=0), name="±1σ", showlegend=True,
    ))
    # Mean line
    fig.add_trace(go.Scatter(
        x=stats["rel_day"], y=stats["mean"] * 100,
        mode="lines+markers",
        line=dict(color=color, width=2.5),
        marker=dict(size=5),
        name=f"{asset} mean CAR",
    ))
    fig.add_vline(x=0, line=dict(color="#F0F6FC", dash="dash", width=1.5))
    fig.add_hline(y=0, line=dict(color=MUTED, width=0.8))

    cycle_str = f" — {cycle_filter}" if cycle_filter != "All" else ""
    _base(fig,
          title=dict(
              text=f"{asset} — Does the Abnormal Return Persist or Reverse?{cycle_str}",
              font=dict(size=16),
          ),
          xaxis_title="Trading Days Relative to RBI Announcement",
          yaxis=dict(gridcolor=GRID, zeroline=False, ticksuffix="%"),
          annotations=[dict(
              x=0.01, y=-0.14, xref="paper", yref="paper",
              text=SOURCE_NOTE, showarrow=False,
              font=dict(size=10, color=MUTED), align="left",
          )],
    )
    return fig


def plot_hike_cut_comparison(car_df: pd.DataFrame, asset: str, horizon: str) -> go.Figure:
    """
    RQ: Do rate hikes and cuts produce asymmetric market reactions?
    Box plot: CAR distribution under Hike vs Cut vs Hold.
    """
    sub   = car_df[car_df["asset"] == asset].copy()
    fig   = go.Figure()
    CYCLE_MAP = {"Hike": HIKE, "Cut": CUT, "Hold": HOLD}

    for cycle, color in CYCLE_MAP.items():
        g = sub[sub["cycle"] == cycle][horizon].dropna() * 100
        if len(g) == 0:
            continue
        fig.add_trace(go.Box(
            y=g.values, name=cycle,
            marker_color=color,
            line_color=color,
            boxmean="sd",
            boxpoints="all",
            jitter=0.3,
            pointpos=0,
        ))

    day_label = horizon.replace("CAR[","[")
    _base(fig,
          title=dict(
              text=f"{asset} CAR {day_label}: Do Hikes and Cuts Produce Asymmetric Reactions?",
              font=dict(size=16),
          ),
          yaxis=dict(gridcolor=GRID, zeroline=True, zerolinecolor=MUTED, ticksuffix="%"),
          xaxis_title="Rate Cycle",
          showlegend=False,
          annotations=[dict(
              x=0.01, y=-0.14, xref="paper", yref="paper",
              text=SOURCE_NOTE, showarrow=False,
              font=dict(size=10, color=MUTED), align="left",
          )],
    )
    return fig


# ─── PAGE 5: Policy Surprise ──────────────────────────────────────────────────

def plot_surprise_scatter(
    merged: pd.DataFrame,
    asset: str,
    horizon: str,
) -> go.Figure:
    """
    RQ: Is a larger policy surprise associated with a larger market reaction?
    Scatter: Surprise_bps (x) vs CAR (y) with OLS trend line.
    """
    sub = merged[merged["asset"] == asset].dropna(subset=["surprise_bps", horizon])
    if len(sub) < 3:
        return go.Figure().update_layout(
            title=f"Insufficient data for {asset} surprise scatter", **_BASE
        )

    color = ASSET_COLORS.get(asset, "#58A6FF")

    fig = go.Figure()
    # Scatter points coloured by cycle
    for cycle, col in [("Hike", HIKE), ("Cut", CUT), ("Hold", HOLD)]:
        g = sub[sub["cycle"] == cycle]
        if len(g) == 0:
            continue
        fig.add_trace(go.Scatter(
            x=g["surprise_bps"],
            y=g[horizon] * 100,
            mode="markers",
            marker=dict(color=col, size=9, opacity=0.85),
            name=cycle,
            text=g["event_date"].dt.strftime("%Y-%m-%d"),
            hovertemplate="%{text}<br>Surprise=%{x}bps<br>CAR=%{y:.3f}%<extra></extra>",
        ))

    # OLS trend line (whole sample)
    xs = sub["surprise_bps"].astype(float).values
    ys = sub[horizon].astype(float).values * 100
    m, b = np.polyfit(xs, ys, 1)
    x_line = np.linspace(xs.min(), xs.max(), 100)
    fig.add_trace(go.Scatter(
        x=x_line, y=m * x_line + b,
        mode="lines",
        line=dict(color="#F0F6FC", width=1.5, dash="dash"),
        name=f"OLS trend (slope={m:.4f})",
        showlegend=True,
    ))

    fig.add_vline(x=0, line=dict(color=MUTED, dash="dot", width=1))
    fig.add_hline(y=0, line=dict(color=MUTED, width=0.8))

    _base(fig,
          title=dict(
              text=f"{asset}: Does a Larger Policy Surprise Drive a Larger {horizon} reaction?",
              font=dict(size=16),
          ),
          xaxis_title="Policy Surprise (bps) = Actual − Expected",
          yaxis=dict(gridcolor=GRID, zeroline=False,
                     title="CAR (%)", ticksuffix="%"),
          annotations=[
              dict(x=0.01, y=-0.14, xref="paper", yref="paper",
                   text=f"N={len(sub)} events with expectations data. {SOURCE_NOTE}",
                   showarrow=False, font=dict(size=9, color=MUTED), align="left"),
          ],
    )
    return fig


def plot_surprise_bar(surprise_df: pd.DataFrame) -> go.Figure:
    """
    Show each surprise event as a bar (surprise magnitude).
    Colours: hawkish surprise = red, dovish = teal, in-line = grey.
    """
    df = surprise_df.sort_values("date")
    colors = [
        HIKE if s == "hawkish" else (CUT if s == "dovish" else HOLD)
        for s in df["surprise_class"]
    ]
    fig = go.Figure(go.Bar(
        x=df["date"].dt.strftime("%Y-%m-%d"),
        y=df["surprise_bps"],
        marker_color=colors,
        text=df["surprise_bps"].apply(lambda x: f"{'+' if x > 0 else ''}{x:.0f}bps"),
        textposition="outside",
        hovertemplate="%{x}<br>Surprise=%{y}bps<extra></extra>",
    ))
    fig.add_hline(y=0, line=dict(color=MUTED, width=1))
    _base(fig,
          title=dict(
              text="Policy Surprise Component by Event — Hawkish vs Dovish vs In-Line",
              font=dict(size=16),
          ),
          xaxis_title="Meeting Date",
          yaxis=dict(gridcolor=GRID, zeroline=True, zerolinecolor=MUTED,
                     title="Surprise (bps) = Actual − Expected"),
          showlegend=False,
          annotations=[dict(
              x=0.01, y=-0.16, xref="paper", yref="paper",
              text="Expectations: Reuters poll medians (2017+). N/A for pre-2017 events.",
              showarrow=False, font=dict(size=9, color=MUTED), align="left",
          )],
    )
    return fig


# ─── PAGE 6: Rate Sensitivity ─────────────────────────────────────────────────

def plot_rate_sensitivity(rate_df: pd.DataFrame) -> go.Figure:
    """
    RQ: Which assets are most sensitive to rate changes, after controlling
        for broad market moves?
    Horizontal bar chart: β₂ (rate sensitivity) by asset.
    """
    df = rate_df.reset_index().sort_values("beta_rate")
    colors = [HIKE if v > 0 else CUT for v in df["beta_rate"]]

    fig = go.Figure(go.Bar(
        y=df["asset"],
        x=df["beta_rate"] * 100,    # % per 100 bps
        orientation="h",
        marker_color=colors,
        text=[f"{v*100:.3f}%" for v in df["beta_rate"]],
        textposition="outside",
    ))

    # Significance stars
    for _, row in df.iterrows():
        star = "**" if row["p_beta_rate"] < 0.01 else ("*" if row["p_beta_rate"] < 0.05 else "")
        if star:
            fig.add_annotation(
                y=row["asset"],
                x=row["beta_rate"] * 100,
                text=f" {star}",
                showarrow=False,
                font=dict(size=14, color=TEXT),
                xanchor="left",
            )

    fig.add_vline(x=0, line=dict(color=MUTED, width=1))
    _base(fig,
          title=dict(
              text="Rate Sensitivity (β₂) — Which Assets Move Most on Rate Change Days?",
              font=dict(size=16),
          ),
          xaxis=dict(
              gridcolor=GRID, zeroline=True, zerolinecolor=MUTED,
              title="β₂ × 100 (% return per 100 bps change)",
          ),
          yaxis=dict(gridcolor=GRID, zeroline=False),
          showlegend=False,
          height=500,
          annotations=[dict(
              x=0.01, y=-0.10, xref="paper", yref="paper",
              text="* p<0.05, ** p<0.01 (Newey-West HAC standard errors). Model: r_asset = α + β₁·r_market + β₂·ΔRate + ε",
              showarrow=False, font=dict(size=9, color=MUTED), align="left",
          )],
    )
    return fig


def plot_stat_test_results(test_df: pd.DataFrame, title: str) -> go.Figure:
    """
    Heatmap of p-values from ACAR significance tests (asset × horizon).
    Green = significant (p<0.05), red = not.
    """
    pivot = test_df.pivot_table(
        index="asset", columns="horizon", values="p_value", aggfunc="mean"
    )
    sig_pivot = test_df.pivot_table(
        index="asset", columns="horizon", values="sig_5pct", aggfunc="mean"
    )

    text = [[
        f"p={pivot.iloc[i,j]:.3f}" + (" ✓" if sig_pivot.iloc[i,j] else "")
        for j in range(pivot.shape[1])
    ] for i in range(pivot.shape[0])]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=list(pivot.columns),
        y=list(pivot.index),
        text=text, texttemplate="%{text}",
        colorscale=[
            [0.00, "#1B4332"], [0.05, "#2D6A4F"],
            [0.10, "#457B9D"],
            [0.50, BG],
            [1.00, "#3D3D3D"],
        ],
        reversescale=True,   # low p = bright
        colorbar=dict(title=dict(text="p-value", font=dict(color=TEXT)),
                      tickfont=dict(color=TEXT)),
        zmin=0, zmax=1,
    ))
    _base(fig,
          title=dict(text=title, font=dict(size=16)),
          margin=dict(l=80, r=40, t=70, b=60),
    )
    return fig


def plot_rolling_beta(
    returns: pd.DataFrame,
    asset: str,
    market_col: str = "Nifty50",
    window: int = 63,
) -> go.Figure:
    """
    Rolling 63-day (≈ 1 quarter) market beta: measures time-varying
    systematic exposure.
    """
    if market_col not in returns.columns or asset not in returns.columns:
        return go.Figure().update_layout(title="Missing data", **_BASE)

    betas = []
    for i in range(window, len(returns)):
        y = returns[asset].iloc[i - window:i].values
        x = returns[market_col].iloc[i - window:i].values
        valid = np.isfinite(x) & np.isfinite(y)
        if valid.sum() < 10:
            betas.append({"date": returns.index[i], "beta": np.nan})
            continue
        cov = np.cov(x[valid], y[valid])
        b   = cov[0, 1] / cov[0, 0]
        betas.append({"date": returns.index[i], "beta": b})

    beta_df = pd.DataFrame(betas).set_index("date")
    color   = ASSET_COLORS.get(asset, "#58A6FF")

    fig = go.Figure(go.Scatter(
        x=beta_df.index, y=beta_df["beta"],
        mode="lines",
        line=dict(color=color, width=2),
        name=f"{asset} β",
    ))
    fig.add_hline(y=1, line=dict(color=MUTED, dash="dot", width=1))
    _base(fig,
          title=dict(
              text=f"{asset} — Rolling {window}-Day Market Beta (vs {market_col})",
              font=dict(size=16),
          ),
          xaxis_title="Date",
          yaxis_title="Beta",
    )
    return fig


# ─── PAGE 7: Research Conclusions ────────────────────────────────────────────

def plot_transmission_summary(car_df: pd.DataFrame) -> go.Figure:
    """
    Summary chart: compare mean Day-0 AR across all assets and cycles.
    This is the headline 'transmission' chart.
    """
    sub = car_df.copy()
    horizon = "CAR[+0,+0]"
    if horizon not in sub.columns:
        return go.Figure().update_layout(title="No data", **_BASE)

    summary = sub.groupby(["asset","cycle"])[horizon].mean().reset_index()
    summary["ar_pct"] = summary[horizon] * 100

    fig = px.bar(
        summary,
        x="asset", y="ar_pct", color="cycle",
        barmode="group",
        color_discrete_map={"Hike": HIKE, "Cut": CUT, "Hold": HOLD},
    )
    fig.update_traces(texttemplate="%{y:.2f}%", textposition="outside")
    _base(fig,
          title=dict(
              text="Monetary Policy Transmission — Mean Day-0 AR by Asset & Cycle",
              font=dict(size=16),
          ),
          xaxis_title="Asset",
          yaxis=dict(gridcolor=GRID, zeroline=True, zerolinecolor=MUTED, ticksuffix="%"),
          annotations=[dict(
              x=0.01, y=-0.14, xref="paper", yref="paper",
              text=SOURCE_NOTE + " | Results subject to small-sample limitations; see Research Report.",
              showarrow=False, font=dict(size=9, color=MUTED), align="left",
          )],
    )
    return fig
