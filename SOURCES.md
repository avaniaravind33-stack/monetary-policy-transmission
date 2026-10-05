# Sources

This document records every data source used in the project. All transformations are noted.
No data is fabricated. Where a required dataset was unavailable, the limitation is flagged
explicitly in the code and research report.

---

## 1. RBI Policy Rate Decisions

| Field | Detail |
|-------|--------|
| Source | Reserve Bank of India — Official Press Releases |
| URL | https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx (individual releases) |
| Date range | January 2014 – September 2025 |
| Variables | Decision date, change in repo rate (bps), new repo rate level, policy stance |
| Transformation | Manually compiled; change_bps computed as (new rate − old rate) × 100; stance categorised from RBI language |
| Limitations | Pre-MPC (pre-October 2016) decisions are Governor's discretionary decisions, not collegial committee votes |

---

## 2. NIFTY 50 (Equity Index)

| Field | Detail |
|-------|--------|
| Source | Yahoo Finance |
| Ticker | `^NSEI` |
| Date range | 2013-01-01 – 2025-09-01 |
| Variable obtained | Adjusted close price (auto_adjust=True) |
| Transformation | Log-return ln(P_t / P_{t-1}) |
| Limitations | NSE/BSE holidays cause gaps; handled via forward-fill only within 5-day lookback |

---

## 3. Bank NIFTY (Banking Sector Index)

| Field | Detail |
|-------|--------|
| Source | Yahoo Finance |
| Ticker | `^NSEBANK` |
| Date range | 2013-01-01 – 2025-09-01 |
| Variable obtained | Adjusted close price |
| Transformation | Log-return |
| Limitations | Concentrated in large-cap private banks; does not fully represent the PSU bank segment |

---

## 4. 10-Year India Government Securities Yield

| Field | Detail |
|-------|--------|
| Source | Yahoo Finance (Reuters feed) |
| Ticker | `IN10YT=RR` |
| Date range | 2013-01-01 – 2025-09-01 |
| Variable obtained | Daily yield level (%) |
| Transformation | First-difference of yield level: Δy = y_t − y_{t-1}. Log-return is **not** used (economically inappropriate for rate series) |
| Limitations | Coverage is patchy pre-2017. Where gaps exceed 5 consecutive trading days around an event, the event is flagged in the data quality log. Cross-check recommended against CCIL/RBI WDM data |

---

## 5. USD/INR Exchange Rate

| Field | Detail |
|-------|--------|
| Source | Yahoo Finance |
| Ticker | `USDINR=X` |
| Date range | 2013-01-01 – 2025-09-01 |
| Variable obtained | Spot rate (INR per USD, adjusted close) |
| Transformation | Log-return (positive = INR depreciation) |
| Limitations | Spot rate; does not capture RBI FX intervention directly. RBI often intervenes in NDF/forward markets which are not reflected |

---

## 6. Individual Bank Stocks

| Field | Detail |
|-------|--------|
| Source | Yahoo Finance |
| Tickers | `HDFCBANK.NS`, `ICICIBANK.NS`, `SBIN.NS`, `KOTAKBANK.NS` |
| Date range | 2013-01-01 – 2025-09-01 |
| Variable obtained | Adjusted close price |
| Transformation | Log-return |
| Limitations | HDFC Bank and HDFC Ltd merged in July 2023; the combined entity is listed as HDFCBANK.NS. Pre-merger data reflects standalone HDFC Bank only |

---

## 7. NSE Sector Indices

| Field | Detail |
|-------|--------|
| Source | Yahoo Finance |
| Tickers | `^CNXIT`, `^CNXAUTO`, `^CNXFMCG`, `^CNXPHARMA`, `^CNXREALTY` |
| Date range | 2013-01-01 – 2025-09-01 |
| Variable obtained | Adjusted close price |
| Transformation | Log-return |
| Limitations | Realty index (`^CNXREALTY`) has relatively thin trading; results for this series treated with additional caution |

---

## 8. Market Expectations / Consensus Forecasts

| Field | Detail |
|-------|--------|
| Source | Reuters pre-meeting polls; Bloomberg survey medians (where cross-referenced in press reports) |
| Date range | Approximately October 2017 – September 2025 |
| Variables | Expected change in repo rate (median consensus, bps) |
| Transformation | Surprise_bps = Actual change − Expected change (median) |
| Limitations | **Critically**: formal pre-meeting surveys did not exist in organised form before 2017. For pre-MPC decisions (2014–2016) and the first year of MPC operation, no organising body published standardised consensus polls. All pre-2017 expected_bps are coded as NaN. We do NOT impute or fabricate these values. |
| Source for specific meetings | Individual Reuters and Bloomberg articles citing poll results, cross-referenced in RBI post-meeting press releases. Available on request. |

---

## 9. RBI Monetary Policy Committee Documents

| Field | Detail |
|-------|--------|
| Source | Reserve Bank of India |
| URL | https://www.rbi.org.in/Scripts/BS_ViewBulletin.aspx (MPC minutes) |
| Date range | October 2016 – present |
| Variables | Policy stance language (accommodative / neutral / withdrawal of accommodation / hawkish), vote counts |
| Transformation | Stance coded as categorical ordinal variable |

---

## Not Used / Explicitly Excluded

| Dataset | Reason Not Used |
|---------|-----------------|
| CCIL WDM bond transaction data | Requires institutional subscription; not publicly accessible |
| SEBI FII/DII flow data | Daily net flows aggregated — correlation with event study not straightforward without tick-level data |
| Bloomberg terminal data | Not publicly available |
| Any proprietary RBI internal data | Not accessible |

---

*All Yahoo Finance data was accessed programmatically via the `yfinance` Python library (v0.2.x+). Download timestamps are preserved in `data/processed/data_quality_log.csv`. Data was accessed between August and October 2025.*
