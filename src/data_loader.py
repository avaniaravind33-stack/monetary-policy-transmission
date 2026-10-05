"""
data_loader.py — Download, validate, and cache all market data.

Assets:
  NIFTY 50          ^NSEI          (NSE benchmark equity index)
  Bank NIFTY        ^NSEBANK       (NSE banking sector index)
  10Y India G-Sec   IN10YT=RR      (Reuters; yfinance may not carry this reliably)
  USD/INR           USDINR=X       (Yahoo Finance FX)
  HDFC Bank         HDFCBANK.NS    (individual bank)
  ICICI Bank        ICICIBANK.NS
  Kotak Bank        KOTAKBANK.NS
  SBI               SBIN.NS

Data quality notes:
  - G-Sec 10Y: Yahoo Finance carries IN10YT=RR but data is patchy for pre-2017.
    We use it where available; where gaps exceed 5 consecutive trading days we flag
    the event as "G-Sec: insufficient data" rather than interpolate.
  - USD/INR: USDINR=X available from 2003; reasonably complete.
  - NSE indices: reliable from 2010; some missing days due to NSE holidays.
  - Bank stocks: HDFC Bank HDFCBANK.NS available from 2002; complete.

Sources documented in SOURCES.md.
"""

import os
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR  = DATA_DIR / "raw"
PROC_DIR = DATA_DIR / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = "2013-01-01"
END_DATE   = "2025-09-01"

# ---------------------------------------------------------------------------
# Asset registry
# ---------------------------------------------------------------------------
ASSET_REGISTRY = {
    # Equity indices
    "Nifty50":   {"ticker": "^NSEI",       "type": "equity_index",  "unit": "index"},
    "BankNifty": {"ticker": "^NSEBANK",    "type": "equity_index",  "unit": "index"},
    # G-Sec proxy — Yahoo Finance carries this with varying coverage
    "GSec10Y":   {"ticker": "IN10YT=RR",   "type": "bond_yield",    "unit": "percent"},
    # FX
    "USDINR":    {"ticker": "USDINR=X",    "type": "fx",            "unit": "INR per USD"},
    # Individual bank stocks
    "HDFC_Bank": {"ticker": "HDFCBANK.NS", "type": "equity_stock",  "unit": "INR"},
    "ICICI_Bank":{"ticker": "ICICIBANK.NS","type": "equity_stock",  "unit": "INR"},
    "SBI":       {"ticker": "SBIN.NS",     "type": "equity_stock",  "unit": "INR"},
    "Kotak_Bank":{"ticker": "KOTAKBANK.NS","type": "equity_stock",  "unit": "INR"},
    # Sector indices (for rate-sensitivity cross-section)
    "IT":        {"ticker": "^CNXIT",      "type": "equity_index",  "unit": "index"},
    "Auto":      {"ticker": "^CNXAUTO",    "type": "equity_index",  "unit": "index"},
    "FMCG":      {"ticker": "^CNXFMCG",   "type": "equity_index",  "unit": "index"},
    "Pharma":    {"ticker": "^CNXPHARMA",  "type": "equity_index",  "unit": "index"},
    "Realty":    {"ticker": "^CNXREALTY",  "type": "equity_index",  "unit": "index"},
}

CACHE_PRICES_FILE  = RAW_DIR / "prices_raw.parquet"
CACHE_RETURNS_FILE = PROC_DIR / "returns_daily.parquet"
QUALITY_LOG_FILE   = PROC_DIR / "data_quality_log.csv"


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_all(force_refresh: bool = False) -> pd.DataFrame:
    """
    Download all assets from Yahoo Finance. Returns a DataFrame of
    daily adjusted Close prices, one column per asset.

    Where yfinance returns empty or very sparse data, we note the gap
    in the data quality log rather than silently dropping or filling.
    """
    if CACHE_PRICES_FILE.exists() and not force_refresh:
        print(f"[data_loader] Loading cached prices from {CACHE_PRICES_FILE}")
        return pd.read_parquet(CACHE_PRICES_FILE)

    print(f"[data_loader] Downloading {len(ASSET_REGISTRY)} assets from Yahoo Finance …")
    frames       = {}
    quality_log  = []

    for name, meta in ASSET_REGISTRY.items():
        ticker = meta["ticker"]
        try:
            raw = yf.download(
                ticker,
                start=START_DATE,
                end=END_DATE,
                progress=False,
                auto_adjust=True,
            )
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)

            if raw.empty:
                print(f"  ⚠️  No data for {name} ({ticker})")
                quality_log.append({
                    "asset": name, "ticker": ticker,
                    "status": "empty", "n_rows": 0,
                    "first_date": None, "last_date": None,
                    "pct_missing": 100.0,
                })
                continue

            close = raw["Close"].rename(name)
            close.index = pd.to_datetime(close.index)

            n_total   = len(close)
            n_missing = close.isna().sum()
            pct_miss  = n_missing / n_total * 100

            frames[name] = close
            quality_log.append({
                "asset":       name,
                "ticker":      ticker,
                "status":      "ok" if pct_miss < 5 else "sparse",
                "n_rows":      n_total,
                "first_date":  str(close.dropna().index[0].date()) if not close.dropna().empty else None,
                "last_date":   str(close.dropna().index[-1].date()) if not close.dropna().empty else None,
                "pct_missing": round(pct_miss, 2),
            })
            flag = "⚠️  sparse" if pct_miss > 5 else "✓"
            print(f"  {flag} {name} ({ticker}): {n_total} rows, {pct_miss:.1f}% missing")

        except Exception as exc:
            print(f"  ✗  ERROR for {name} ({ticker}): {exc}")
            quality_log.append({
                "asset": name, "ticker": ticker,
                "status": "error", "n_rows": 0,
                "first_date": None, "last_date": None,
                "pct_missing": 100.0,
            })

    if not frames:
        raise RuntimeError(
            "No data downloaded from Yahoo Finance. "
            "Check your internet connection and try again."
        )

    prices = pd.concat(frames, axis=1)
    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index()

    # Save quality log
    pd.DataFrame(quality_log).to_csv(QUALITY_LOG_FILE, index=False)
    print(f"[data_loader] Data quality log → {QUALITY_LOG_FILE}")

    prices.to_parquet(CACHE_PRICES_FILE)
    print(f"[data_loader] Prices cached → {CACHE_PRICES_FILE}")

    return prices


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

def compute_returns(
    prices: pd.DataFrame,
    yield_cols: list[str] | None = None,
) -> pd.DataFrame:
    """
    Compute daily returns.
    - For price assets (equity, FX): log return = ln(P_t / P_{t-1})
    - For yield assets (G-Sec 10Y): first difference of yield level (Δy)
      because yields are already rates; taking log-returns of yields is
      economically inappropriate when yield is near zero.

    Parameters
    ----------
    prices    : raw price / level DataFrame
    yield_cols: list of column names that are yield levels (not prices).
                Default: ["GSec10Y"]
    """
    if yield_cols is None:
        yield_cols = [c for c in prices.columns if c in ("GSec10Y",)]

    price_cols = [c for c in prices.columns if c not in yield_cols]

    returns = pd.DataFrame(index=prices.index)

    if price_cols:
        log_ret = np.log(prices[price_cols] / prices[price_cols].shift(1))
        returns = pd.concat([returns, log_ret], axis=1)

    if yield_cols:
        present_yield_cols = [c for c in yield_cols if c in prices.columns]
        if present_yield_cols:
            diff_yield = prices[present_yield_cols].diff()   # Δy in percentage points
            returns = pd.concat([returns, diff_yield], axis=1)

    returns = returns.dropna(how="all")
    return returns


def get_event_window_data(
    asset_data: pd.DataFrame,
    event_date: pd.Timestamp,
    windows: list[int] | None = None,
) -> dict:
    """
    For a given event date, return levels / changes at specified relative days.

    windows: relative trading days from event day.
             Default: [-1, 0, +1, +3, +5]

    Returns a dict: {rel_day: {col: value}}
    """
    if windows is None:
        windows = [-1, 0, 1, 3, 5]

    idx = asset_data.index
    try:
        t0_loc = idx.get_loc(event_date)
    except KeyError:
        # Find nearest subsequent trading day
        t0_loc = None
        for lag in range(1, 6):
            d = event_date + pd.Timedelta(days=lag)
            if d in idx:
                t0_loc = idx.get_loc(d)
                break
    if t0_loc is None:
        return {}

    result = {}
    for w in windows:
        target_loc = t0_loc + w
        if 0 <= target_loc < len(idx):
            result[w] = asset_data.iloc[target_loc].to_dict()
    return result


def load_quality_log() -> pd.DataFrame:
    """Return the data quality log generated during last download."""
    if QUALITY_LOG_FILE.exists():
        return pd.read_csv(QUALITY_LOG_FILE)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Fallback synthetic data
# ---------------------------------------------------------------------------

def generate_synthetic_data() -> pd.DataFrame:
    """
    Generate GBM synthetic prices for offline/CI mode.
    Parameters calibrated to approximate historical Indian market levels and vol.
    Clearly labelled as synthetic — never used for real inferential conclusions.
    """
    print("[data_loader] ⚠️  Generating SYNTHETIC benchmark data (offline mode).")
    print("              Results with this data are for demonstration only. Do not cite as findings.")

    rng   = np.random.default_rng(42)
    dates = pd.bdate_range(START_DATE, END_DATE)
    n     = len(dates)
    dt    = 1 / 252

    params = {
        "Nifty50":    (0.12, 0.14, 6000),
        "BankNifty":  (0.13, 0.22, 11000),
        "GSec10Y":    None,  # handle separately
        "USDINR":     (0.04,  0.05, 62.0),
        "HDFC_Bank":  (0.15, 0.20, 700),
        "ICICI_Bank": (0.14, 0.22, 300),
        "SBI":        (0.10, 0.25, 200),
        "Kotak_Bank": (0.16, 0.21, 600),
        "IT":         (0.15, 0.23, 9000),
        "Auto":       (0.11, 0.20, 4500),
        "FMCG":       (0.10, 0.14, 7000),
        "Pharma":     (0.11, 0.18, 5500),
        "Realty":     (0.08, 0.30,  200),
    }

    frames = {}
    for col, p in params.items():
        if col == "GSec10Y":
            # Simulate a yield series (mean-reverting AR(1) around 7%)
            yields = [7.5]
            for _ in range(n - 1):
                shock   = rng.normal(0, 0.03)
                y_new   = yields[-1] + 0.01 * (7.0 - yields[-1]) + shock
                y_new   = max(3.0, min(12.0, y_new))
                yields.append(y_new)
            frames[col] = pd.Series(yields, index=dates, name=col)
        else:
            mu, sig, base = p
            shocks = rng.normal((mu - 0.5 * sig**2) * dt, sig * np.sqrt(dt), n)
            price  = base * np.exp(np.cumsum(shocks))
            frames[col] = pd.Series(price, index=dates, name=col)

    prices = pd.DataFrame(frames)
    prices.index.name = "Date"
    return prices


if __name__ == "__main__":
    prices = download_all(force_refresh=False)
    if prices.empty:
        prices = generate_synthetic_data()
    returns = compute_returns(prices)
    print(f"\nPrices shape : {prices.shape}")
    print(f"Returns shape: {returns.shape}")
    print(returns.tail(3))
    ql = load_quality_log()
    if not ql.empty:
        print("\nData quality summary:")
        print(ql[["asset","status","pct_missing"]].to_string(index=False))
