# Monetary Policy Transmission & Indian Asset Markets

**A Goldman-Sachs GIR–style event-study research project**

---

## Research Question

> How do Reserve Bank of India monetary-policy decisions transmit into Indian equities
> (NIFTY 50, Bank NIFTY), government bond yields (10Y G-Sec), and the INR/USD
> exchange rate — and does the market reaction differ between **expected** and
> **unexpected** policy decisions?

---

## Motivation

Monetary policy transmission is a core question in macro-finance. The RBI's
Monetary Policy Committee (MPC), formally constituted in October 2016, has
been the locus of Indian rate-setting since then. Its decisions affect borrowing
costs for households and firms, the term structure of interest rates, and the
relative attractiveness of Indian assets for global investors.

This project applies the **event-study methodology** (standard in academic
finance since Fama et al., 1969 and MacKinlay, 1997) to quantify:

1. The **average abnormal return (ACAR)** in Indian assets around MPC meetings.
2. Whether the direction of the rate decision (hike vs cut) matters asymmetrically.
3. Whether the **surprise component** — deviation from consensus expectations —
   drives the magnitude of the market reaction.
4. Which asset classes are most **rate-sensitive** (β₂) after controlling for
   broad market moves.

---

## Project Structure

```
monetary-policy-transmission/
├── src/
│   ├── rbi_events.py          # Full RBI policy calendar (2013–2025), with surprise data
│   ├── data_loader.py         # Yahoo Finance download, quality logging, returns
│   ├── event_study.py         # Event-study engine (AR, CAR, ACAR, β₂)
│   ├── policy_surprise.py     # Surprise classification, regression, t-test
│   └── statistical_tests.py   # Batch significance tests, Kruskal-Wallis
│   └── visualizations.py      # All Plotly charts
├── dashboard/
│   └── app.py                 # 7-page Streamlit dashboard
├── notebooks/
│   └── full_analysis.ipynb    # End-to-end research notebook
├── data/
│   ├── raw/                   # prices_raw.parquet (gitignored)
│   └── processed/             # returns, CAR outputs, quality log
├── outputs/
│   └── *.xlsx                 # Excel-compatible result exports
├── research_report/
│   └── monetary_policy_transmission.md
├── SOURCES.md                 # Full data provenance
├── README.md                  # This file
└── requirements.txt
```

---

## Methodology

### Event-Study Framework
- **Estimation window**: [t−120, t−21] trading days (≈100 trading days of clean data before a 20-day quiet period)
- **Event windows**: {−1, 0}, {0}, {0, +1}, {0, +3}, {0, +5} relative trading days
- **Market model** (equity & FX): `r_asset = α + β·r_Nifty50 + ε`, fit on estimation window; AR = residual on event days
- **Yield model** (G-Sec 10Y): constant-mean model — AR = Δy − mean(Δy over estimation window). Log-returns are not used for yield series (economically inappropriate near zero).
- **CAR** (Cumulative Abnormal Return): sum of ARs over a window
- **ACAR**: cross-event average of CARs

### Policy Surprise
- `Surprise_bps = Actual_change − Expected_change` (Reuters poll median)
- Expectations data available for MPC meetings from approximately 2017 onwards
- Pre-2017 expected_bps are coded `NaN` — never imputed or fabricated
- Surprise regression: `CAR = γ₀ + γ₁·Surprise_bps + ε`, HC3 standard errors (White-corrected)

### Rate Sensitivity (β₂)
- Full-sample OLS: `r_asset,t = α + β₁·r_market,t + β₂·RateChange_bps,t + ε`
- RateChange_bps is non-zero only on event days (the actual bps change)
- Newey-West HAC standard errors (maxlags=5)

### Statistical Tests
1. One-sample t-test: H₀: ACAR = 0
2. Welch two-sample t-test: H₀: ACAR(Hike) = ACAR(Cut)
3. Kruskal-Wallis: H₀: CAR distribution identical across regimes (robustness)
4. OLS regression: |CAR| ~ |ΔRate| (magnitude effect)
5. Multiple testing: Bonferroni correction noted throughout

---

## Data Sources

| Asset | Ticker | Source |
|-------|--------|--------|
| NIFTY 50 | ^NSEI | Yahoo Finance |
| Bank NIFTY | ^NSEBANK | Yahoo Finance |
| 10Y G-Sec yield | IN10YT=RR | Yahoo Finance (Reuters) |
| USD/INR | USDINR=X | Yahoo Finance |
| HDFC Bank | HDFCBANK.NS | Yahoo Finance |
| ICICI Bank | ICICIBANK.NS | Yahoo Finance |
| SBI | SBIN.NS | Yahoo Finance |
| Kotak Bank | KOTAKBANK.NS | Yahoo Finance |
| IT, Auto, FMCG, Pharma, Realty sectors | ^CNXIT etc. | Yahoo Finance |
| RBI rate decisions | — | RBI.org.in press releases |
| Market expectations | — | Reuters/Bloomberg polls (2017+ only) |

Full provenance: see [`SOURCES.md`](SOURCES.md)

---

## Key Assumptions & Limitations

- **Small N**: Cycle-specific subsamples have ~8–12 events. Statistical power is limited.
- **Event clustering**: March–May 2020 emergency COVID cuts may share market conditions. Robustness checks excluding these are provided.
- **Market model**: Nifty50 is used as the market factor for all equity assets. A more complete model would use Fama-French India factors (unavailable publicly).
- **G-Sec data gaps**: IN10YT=RR (Yahoo/Reuters) has patchy coverage pre-2017. Events with >5 consecutive missing yield days are flagged.
- **Expectations data**: Available post-2017 only (Reuters polls). No imputation for pre-2017 data.
- **Endogeneity**: The RBI does not set rates randomly — decisions are correlated with macroeconomic conditions that also affect asset prices. This project does not claim causal identification.
- **Multiple testing**: Many tests are run. Results crossing only uncorrected 5% threshold are marked "suggestive."

---

## How to Run

### 1. Install dependencies

```bash
cd monetary-policy-transmission
pip install -r requirements.txt
```

### 2. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard will attempt to download market data from Yahoo Finance on first run and cache it locally to `data/raw/prices_raw.parquet`. If the download fails (no internet), it falls back to synthetic GBM data and clearly flags all results as illustrative.

### 3. Run the full pipeline from Python

```python
from src.data_loader import download_all, compute_returns
from src.rbi_events  import get_full_calendar
from src.event_study import run_event_study, run_rate_sensitivity

events  = get_full_calendar()
prices  = download_all()
returns = compute_returns(prices)
result  = run_event_study(returns, events)

car_df  = result["car_panel"]   # wide-form CAR × asset × horizon
ar_df   = result["ar_panel"]    # long-form AR × event × asset × day
ev_log  = result["event_log"]   # events with data quality flags
```

### 4. Force data refresh

```python
from src.data_loader import download_all
prices = download_all(force_refresh=True)
```

---

## Reproducibility

- All random seeds fixed (`np.random.default_rng(42)` in synthetic data generator).
- Data download is deterministic given the same Yahoo Finance API state.
- All test results are computed deterministically from the downloaded data.
- The event calendar (`src/rbi_events.py`) is manually curated and version-controlled.

---

## References

- Fama, E.F., L. Fisher, M.C. Jensen, and R. Roll (1969). "The Adjustment of Stock Prices to New Information." *International Economic Review*.
- MacKinlay, A.C. (1997). "Event Studies in Economics and Finance." *Journal of Economic Literature*.
- Patell, J.M. (1976). "Corporate Forecasts of Earnings Per Share and Stock Price Behavior." *Journal of Accounting Research*.
- Boehmer, E., J. Musumeci, and A.B. Poulsen (1991). "Event-Study Methodology Under Conditions of Event-Induced Variance." *Journal of Financial Economics*.
- Bernanke, B. and K. Kuttner (2005). "What Explains the Stock Market's Reaction to Federal Reserve Policy?" *Journal of Finance*.
- Reserve Bank of India (various years). Monetary Policy Statements and Press Releases. https://www.rbi.org.in

---

## Author Note

This project was built as part of a portfolio demonstrating research-grade
quantitative finance methodology. It follows Goldman Sachs Global Investment
Research standards for intellectual rigour: explicit data sourcing, stated
limitations, and no fabrication of results or conclusions.
