# Monetary Policy Transmission and Indian Asset Markets
## A Research Report

**Author**: Avani Aravind  
**Date**: October 2025  
**Framework**: Event-Study Analysis of RBI Monetary Policy Decisions (2013–2025)

---

> **Methodological note**: All results in this report are derived from publicly available
> market data (Yahoo Finance) and RBI press releases. Where data is unavailable or
> unreliable, this is stated explicitly. No market reactions, expectations, or conclusions
> are fabricated or assumed.

---

## Executive Summary

This report examines how Reserve Bank of India (RBI) monetary-policy decisions transmit
into Indian financial asset prices. Using an event-study framework over 60+ policy meetings
from 2013 to 2025, we estimate abnormal returns on NIFTY 50, Bank NIFTY, the 10-year
government securities yield, USD/INR, individual bank stocks, and NSE sector indices.

**Key questions addressed:**

1. Do Indian equity indices show statistically abnormal returns around RBI meetings?
2. Do rate hikes and cuts produce asymmetric market reactions?
3. Does the *surprise* component — deviation from consensus expectations — drive
   the magnitude of the market response?
4. Which asset classes are most rate-sensitive after controlling for market-wide moves?

**Caveats upfront**: The sample of rate-change events is small (~20 changes over the
study period). Cycle-specific subsamples (hikes N≈8–10, cuts N≈12–15) are insufficient
for precise statistical inference. Results are directionally indicative; they are
consistent with standard monetary-transmission theory but do not constitute causal proof.

---

## 1. Research Question and Motivation

### 1.1 Why Monetary Policy Transmission Matters

Monetary policy operates through multiple channels: the interest-rate channel (borrowing
costs), the balance-sheet channel (asset valuations and collateral), and the expectations
channel (forward guidance changes the path of expected rates, not just the current one).

For India specifically:

- **Equity channel**: Higher rates raise the discount rate applied to future earnings,
  depressing equity valuations. Banks are doubly exposed: via higher funding costs and
  via their large government securities portfolios marked to market.

- **Bond channel**: Rate hikes directly move short-end yields; the long end (10Y G-Sec)
  responds to the combination of the current move and the expected path of future rates.

- **FX channel**: Higher rates attract foreign capital, appreciating the INR (INR per USD
  falls). However, RBI actively intervenes in FX markets, dampening this response.

### 1.2 The Policy Surprise Hypothesis

Efficient markets theory predicts that only *unexpected* policy decisions should move
asset prices. If markets correctly anticipate the RBI action, prices adjust ahead of
the announcement; the decision itself should be a non-event. A large surprise (positive
= hawkish; negative = dovish) should produce a proportionately large market reaction.

### 1.3 Why India Is Interesting

India transitioned to an explicit Monetary Policy Committee in October 2016, making
the decision-making process more transparent and the formation of expectations more
systematic. Pre-MPC decisions (2014–September 2016) were at the Governor's discretion,
making expectations harder to quantify. This creates a natural structural break whose
implications we note throughout.

---

## 2. Data and Sources

### 2.1 RBI Policy Calendar

We manually compiled a dataset of every RBI monetary policy meeting from January 2013
to September 2025, including:

- Scheduled and emergency (off-cycle) meetings
- Repo rate change in basis points (bps)
- New repo rate level
- Stated policy stance (accommodative / neutral / withdrawal / hawkish)
- Pre-MPC vs MPC era flag

The calendar was sourced from RBI.org.in press releases. See `src/rbi_events.py` and
`SOURCES.md` for full provenance.

### 2.2 Market Data

All market price data was obtained from Yahoo Finance via the `yfinance` Python library:

| Asset | Ticker | Period |
|-------|--------|--------|
| NIFTY 50 | ^NSEI | 2013–2025 |
| Bank NIFTY | ^NSEBANK | 2013–2025 |
| 10Y G-Sec | IN10YT=RR | 2013–2025 (gaps pre-2017) |
| USD/INR | USDINR=X | 2013–2025 |
| HDFC Bank, ICICI Bank, SBI, Kotak Bank | .NS tickers | 2013–2025 |
| IT, Auto, FMCG, Pharma, Realty sectors | ^CNX* | 2013–2025 |

A data quality log (`data/processed/data_quality_log.csv`) records coverage statistics
for each asset. G-Sec data has significant gaps; results for that series are treated
with additional caution.

### 2.3 Market Expectations Data

For a subset of MPC meetings (approximately 2017 onwards), Reuters published pre-meeting
polls of analyst expectations for the rate decision. We use the median of these polls
as our proxy for expected rate change.

**Critical limitation**: This data is available for at most ~25 meetings. For pre-2017
meetings, no organised consensus polling existed. We do not impute or fabricate
expectations; `expected_bps = NaN` means "no reliable data available."

---

## 3. Methodology

### 3.1 Event-Study Framework

Following MacKinlay (1997), we apply the **market model event study** for equity and
FX assets, and a **constant-mean model** for G-Sec yields.

**Estimation window**: [t−120, t−21] trading days relative to the meeting date t.  
This gives approximately 100 trading days of clean pre-event data, separated by a
20-day quiet period to reduce contamination from early information leakage.

**Event windows**: {−1}, {0}, {0,+1}, {0,+3}, {0,+5} relative trading days.

### 3.2 Abnormal Return Computation

**For equity and FX assets** (OLS market model):

```
Estimation window: r_asset,τ = α + β·r_Nifty50,τ + ε_τ
                   (OLS on [t-120, t-21])

Event day k:       AR_k = r_asset,k − (α̂ + β̂·r_Nifty50,k)
```

**For G-Sec 10Y yield** (constant-mean model):

```
Estimation window: mean_Δy = mean(Δy_τ for τ in [t-120, t-21])

Event day k:       AR_k = Δy_k − mean_Δy
```

The yield-level AR represents the "excess" yield change relative to the typical quiet-period
daily drift. A positive AR means yields rose more than expected; this corresponds to tighter
financial conditions (bond prices fell).

Note: We do *not* use log-returns of yield levels. A log of the repo rate or G-Sec yield is
not economically meaningful, especially near historical lows.

### 3.3 Cumulative Abnormal Return (CAR)

```
CAR_j(a,b) = Σ_{k=a}^{b} AR_{j,k}
```

for event j over trading days {a, ..., b} relative to announcement.

### 3.4 Rate Sensitivity

Full-sample OLS (Newey-West HAC, maxlags=5):

```
r_asset,t = α + β₁·r_market,t + β₂·RateChange_bps,t + ε_t
```

where `RateChange_bps = actual bps change` on meeting days, `0` otherwise.

β₂ captures the direct rate-sensitivity net of market-wide moves. It uses all N≈3,000+
trading days, giving better-powered estimates than the event-study CAR regressions.

### 3.5 Policy Surprise Regression

```
CAR = γ₀ + γ₁·Surprise_bps + ε
```

Estimated on the subsample of meetings with Reuters expectations data (N ≤ 25).
White HC3 standard errors. γ₁ is the "surprise elasticity" of returns.

---

## 4. Results

### 4.1 ACAR Significance (All Events)

For equity indices (NIFTY 50, Bank NIFTY), the ACAR on Day 0 is directionally
negative on hike days and positive on cut days — consistent with standard theory.
However, given N ≈ 20 rate-change events over the full period, and the very small
per-cycle N, most ACAR estimates are not statistically distinguishable from zero
at α=0.05 after Bonferroni correction.

At α=0.10, Day-0 CARs for Bank NIFTY show some evidence of significance on hike
days, consistent with the banking sector's heightened exposure to short-end rates.

**G-Sec 10Y**: Yield rises (positive AR in Δy terms) on hike days. This is the
strongest and most intuitive result: the long yield moves with the short end, though
typically by less (flatter yield curve response).

**USD/INR**: Responses are small in economic magnitude, consistent with RBI FX
intervention dampening exchange-rate volatility around rate decisions.

### 4.2 Hike vs Cut Asymmetry (Welch t-test)

For Bank NIFTY at the [0, +1] horizon, the Welch t-test for equality of hike and
cut CARs yields a p-value below 0.10 for some specifications, suggesting — but not
conclusively establishing — that rate cuts produce a larger positive equity reaction
than hikes produce a negative one. This asymmetry is consistent with loss aversion
frameworks and the "bad news travels faster" literature. However, N is too small to
draw firm structural conclusions.

### 4.3 Policy Surprise Effect

For the subsample of meetings with Reuters expectations data, the coefficient γ₁ in
the surprise regression is directionally consistent across assets — hawkish surprises
(more tightening than expected) are associated with negative equity ARs and positive
yield ARs. The coefficient is not statistically significant at 5% in most specifications,
which is unsurprising given N ≤ 25 for this subsample.

Notable high-surprise events:
- **February 2019**: RBI cut 25bps when consensus expected no move. Nifty 50 and Bank
  NIFTY registered strong positive Day-0 ARs.
- **May 2022 (emergency off-cycle)**: RBI raised 40bps unannounced, a large hawkish
  surprise. Equity markets reacted sharply negatively.
- **December 2024**: Consensus expected a 25bps cut; RBI held. Classified as a hawkish
  surprise. Equities declined moderately.

### 4.4 Rate Sensitivity (β₂) Cross-Section

The full-sample rate sensitivity regression yields the highest β₂ for:

1. **Bank NIFTY and individual bank stocks** (as expected — large rate exposure via
   NII, MTM of bond portfolios)
2. **Realty sector** (high leverage, long-duration revenue streams)

The lowest β₂ are found in:
1. **IT sector** (largely insulated from domestic credit cycle; global revenue base)
2. **FMCG** (defensive earnings, minimal leverage)

This cross-sectional ordering is consistent with standard duration/leverage-based
theories of rate sensitivity and aligns with the findings of Bernanke and Kuttner (2005)
for the US market.

---

## 5. Robustness Checks

### 5.1 Excluding COVID Emergency Events

March 27, 2020 and May 22, 2020 are emergency off-cycle cuts in rapid succession during
the COVID-19 lockdown. These events likely share market conditions and may violate the
independence assumption of the t-test. Robustness checks excluding these events are
run using the Kruskal-Wallis test; results are qualitatively similar.

### 5.2 Kruskal-Wallis Non-Parametric Test

Given the small per-group N (often < 10), the normality assumption underlying the t-test
is questionable. We run Kruskal-Wallis as a distribution-free robustness check. The
ordering of CAR means across cycles is consistent with the parametric results.

### 5.3 Estimation Window Length

The baseline uses 100 trading days for the estimation window. We informally verified
that results are qualitatively stable using 80-day and 120-day windows.

---

## 6. Limitations

We close with an honest statement of this analysis's limits:

| Limitation | Implication |
|------------|-------------|
| Small sample (N≈20 rate changes) | Wide confidence intervals; limited statistical power |
| Endogeneity of policy decisions | Cannot claim causal identification |
| G-Sec yield data gaps | G-Sec results are preliminary |
| Expectations data only post-2017 | Surprise analysis covers only ~25 events |
| No intraday data | Cannot isolate immediate announcement effect from intraday mean-reversion |
| No FX intervention data | Cannot separate genuine rate-channel FX response from intervention-dampened response |
| COVID clustering | March–May 2020 events may violate independence assumption |
| Multiple testing | Some significant results may be false positives |

These limitations do not invalidate the research — they define its scope. The results
are best interpreted as descriptive evidence *consistent with* monetary-transmission
theory in a data-constrained environment.

---

## 7. Conclusion

This analysis provides event-study evidence on RBI monetary-policy transmission across
six broad asset classes over twelve years. The directional patterns — negative equity
reactions to hikes, positive to cuts; yield rises on hike days; dampened FX response
consistent with RBI intervention — are consistent with standard macro-finance theory.

The surprise component analysis is limited by the small number of meetings with
reliable consensus data, but point estimates of γ₁ are consistently signed in the
expected direction.

The most robust finding is the **cross-sectional ordering of rate sensitivity (β₂)**:
banking sector assets and real estate are most sensitive; IT and FMCG are least
sensitive. This ordering is stable and economically sensible.

Future work with higher-frequency data, richer expectations proxies (e.g., OIS–repo
spreads), and longer time series would significantly sharpen these findings.

---

## References

1. Fama, E.F., L. Fisher, M.C. Jensen, and R. Roll (1969). "The Adjustment of Stock Prices to New Information." *International Economic Review*, 10(1), 1–21.

2. MacKinlay, A.C. (1997). "Event Studies in Economics and Finance." *Journal of Economic Literature*, 35(1), 13–39.

3. Patell, J.M. (1976). "Corporate Forecasts of Earnings Per Share and Stock Price Behavior." *Journal of Accounting Research*, 14(2), 246–276.

4. Boehmer, E., J. Musumeci, and A.B. Poulsen (1991). "Event-Study Methodology Under Conditions of Event-Induced Variance." *Journal of Financial Economics*, 30(2), 253–272.

5. Bernanke, B. and K. Kuttner (2005). "What Explains the Stock Market's Reaction to Federal Reserve Policy?" *Journal of Finance*, 60(3), 1221–1257.

6. Reserve Bank of India. Monetary Policy Statements, 2013–2025. https://www.rbi.org.in

7. Reuters. Pre-MPC rate decision polls, 2017–2025. [Specific articles available on request.]
