"""
Asset Comparison Dashboard

This Streamlit app visualizes the relationship between various assets and key Market Index
indicators such as the S&P 500 (SPY), and Nasdaq-100 (QQQ). It allows users to explore 
price trends, correlations, and normalized percentage changes over customizable time ranges.

Features:
- Interactive chart with optional normalization (percent change from baseline)
- Sidebar toggles to include/exclude individual tickers
- Preset and custom date ranges with inclusive start and end dates

Reference:
- https://medium.com/@kasperjuunge/yfinance-10-ways-to-get-stock-data-with-python-6677f49e8282
"""

from datetime import date, datetime
import time
import re

import streamlit as st
import tzlocal

from btc_macro.charts import build_comparison_chart
from btc_macro.dates import RANGE_OPTIONS, range_start, resolve_date_range
from btc_macro.transforms import normalize_prices, prepare_price_data
from btc_macro.yahoo import (
    apply_current_prices,
    download_close_prices,
    fetch_current_prices,
    ticker_has_recent_data,
)

# Get local timezone automatically
local_tz = tzlocal.get_localzone()

# Get *now* in your local timezone, and strip to date
local_today = datetime.now(local_tz).date()

# --- Set Page layout and titles ---
st.set_page_config(layout="wide")
st.title("📈 Asset Comparison")

# --- User Selected Options. Must be valid Ticker Symbol ---
tickers = ["SPY", "EFA", "IWM", "QQQ", "STRK", "NVDA", "AAPL", "TSLA",
           "^DJI", "DX-Y.NYB", "GC=F", "SI=F", "HG=F",
           "BTC-USD", "ETH-USD", "SOL-USD"
           ]
default_tickers = ["SPY", "IWM", "EFA", "QQQ"]

# --- Session_State initialization to establish stable defaults ---
def init_state():
    st.session_state.setdefault("applied_params", None)   # dict of last-applied settings
    st.session_state.setdefault("ticker_list", tickers.copy())
    st.session_state.setdefault("selected_assets", default_tickers.copy())
    st.session_state.setdefault("user_input", "")
    st.session_state.setdefault("add_ticker_error", "")
    st.session_state.setdefault("add_ticker_error_expires", 0.0)

init_state()

# --- Validate Ticker Symbol ---
@st.cache_data(ttl=24*3600)
def is_valid_ticker(symbol):
    ''' Make a minimal request to validate ticker is valid '''
    return ticker_has_recent_data(symbol)

# --- Fetch Ticker Price Data ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_yf_data(sel_tickers_key: tuple[str, ...], starting_date: str, ending_date: str):
    """Cache closing prices by tickers and both inclusive date bounds."""
    return download_close_prices(
        list(sel_tickers_key), starting_date, ending_date=ending_date,
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_current_prices(tickers_key: tuple[str, ...]) -> dict[str, float]:
    """Return briefly cached current prices for 24/7 assets."""
    return fetch_current_prices(list(tickers_key))

# Allow common Yahoo formats: BRK.B, BTC-USD, GC=F, ^GSPC, DX-Y.NYB, etc.
_TICKER_RE = re.compile(r"^[A-Z0-9.\-=\^]+$")

def add_ticker():
    """Callback: add a single user-supplied ticker to options + selection."""
    raw = st.session_state.get("user_input", "")
    new_ticker = raw.strip().upper()
    st.session_state.user_input = ""

    if not new_ticker:
        return

    # Reject multi-ticker entry (your "TSLA, IBM" case)
    if any(sep in new_ticker for sep in [",", " ", ";", "\n", "\t"]):
        st.session_state.add_ticker_error = "Enter exactly ONE ticker (no commas or spaces)."
        st.session_state.add_ticker_error_expires = time.time() + 2
        return

    # Reject obviously invalid characters early (before calling yfinance)
    if not _TICKER_RE.match(new_ticker):
        st.session_state.add_ticker_error = "Ticker contains invalid characters."
        st.session_state.add_ticker_error_expires = time.time() + 2
        return

    # If ticker is already present + already selected, do nothing
    already_in_list = new_ticker in st.session_state.ticker_list
    already_selected = new_ticker in st.session_state.get("selected_assets", [])
    if already_in_list and already_selected:
        st.session_state.add_ticker_error = f"{new_ticker} is already selected."
        st.session_state.add_ticker_error_expires = time.time() + 1.5
        return

    # Now do your existing validity check and add new ticker if valid
    if is_valid_ticker(new_ticker):
        if new_ticker not in st.session_state.ticker_list:
            st.session_state.ticker_list.append(new_ticker)
        if new_ticker not in st.session_state.selected_assets:
            cur = list(st.session_state.selected_assets)
            if new_ticker not in cur:
                cur.append(new_ticker)
            st.session_state.selected_assets = cur

        # Clear any prior error
        st.session_state.add_ticker_error = ""
        st.session_state.add_ticker_error_expires = 0.0
    else:
        st.session_state.add_ticker_error = f"Sorry, {new_ticker} is not a valid ticker."
        st.session_state.add_ticker_error_expires = time.time() + 2

# --- Create sidebar Widgets ---
with st.sidebar:
    selected_range = st.selectbox("Time Range", options=[*RANGE_OPTIONS, "Custom"])
    custom_start = custom_end = None
    custom_submitted = False
    if selected_range == "Custom":
        saved_start, saved_end = st.session_state.get(
            "custom_date_range", (range_start("1 Month", local_today), local_today),
        )
        with st.form("custom_dates"):
            custom_start = st.date_input(
                "Start date", value=saved_start,
                min_value=date(1900, 1, 1), max_value=local_today,
                key="custom_start", format="YYYY-MM-DD",
            )
            custom_end = st.date_input(
                "End date", value=saved_end,
                min_value=date(1900, 1, 1), max_value=local_today,
                key="custom_end", format="YYYY-MM-DD",
            )
            st.caption("Both dates are included. Historical ranges use closing prices only.")
            custom_submitted = st.form_submit_button("Apply dates")
    st.divider()
    st.multiselect(
        "Select Assets", 
        options=list(st.session_state.ticker_list),
        key="selected_assets"   # <- lets Streamlit manage and persist selection
    )
    st.text_input("Add ticker", key="user_input", on_change=add_ticker, placeholder="e.g., TSLA")

    msg = st.session_state.get("add_ticker_error", "")
    expires = st.session_state.get("add_ticker_error_expires", 0.0)
    if msg and time.time() < expires:
        st.error(msg)
    st.divider()
    view = st.radio("Chart Type", ["Closing Price (USD)", "Normalized % Change"], index=1)

# Create a placeholder slots for progress status updates and chart.
chart_ph = st.empty()     # chart lives here
status_ph = st.empty()    # status lives here

try:
    start_date, end_date = resolve_date_range(
        selected_range, local_today, custom_start, custom_end,
    )
except ValueError as e:
    chart_ph.warning(str(e))
    st.stop()

if custom_submitted:
    # Separate from widget keys, which Streamlit removes while Custom is hidden.
    st.session_state.custom_date_range = (start_date, end_date)

# If for some reason user hasn't selected any tickers, warn and stop
selected_assets = st.session_state.get("selected_assets", [])
if not selected_assets:
    chart_ph.warning("No assets selected. Choose one or more tickers in the sidebar.")
    st.stop()

# This main section does the real work while updating the user on progress
with status_ph.status("Fetching market data…", expanded=True) as status:
    # --- Make sure we have the latest list of tickers ---
    selected_assets = st.session_state.selected_assets.copy()

    # --- Determine if we're using Narmalized or Price view ---
    is_norm = view == "Normalized % Change"

    days_back = (end_date - start_date).days

    # Downloading once also verifies connectivity and identifies missing tickers.
    status.write(f"Downloading price data: {', '.join(selected_assets)}")
    tickers_key = tuple(sorted(selected_assets))
    start_key = start_date.isoformat()
    end_key = end_date.isoformat()

    try:
        data = get_yf_data(tickers_key, start_key, end_key)
    except RuntimeError as e:
        st.error(f"Download failed: {e}")
        st.stop()

    # Align downloaded observations and remove assets with no usable data.
    filtered_data, all_nan_assets = prepare_price_data(
        data,
        selected_assets,
        start_date,
        end_date,
    )
    if all_nan_assets:
        st.warning(
            f"Removed asset(s) with no data in selected range: {', '.join(all_nan_assets)}"
        )

    # Final guard: stop if nothing remains
    if filtered_data.empty:
        st.error("No valid price data available for the selected assets and date range.")
        st.stop()

    # --- Looks like we're good to proceed so sync selected_assets with filtered data ---
    selected_assets = filtered_data.columns.tolist()

    # Only a range ending today may include current crypto quotes.
    crypto_assets = tuple(ticker for ticker in selected_assets if "-USD" in ticker)
    if end_date == local_today and crypto_assets:
        filtered_data = apply_current_prices(
            filtered_data,
            get_current_prices(crypto_assets),
            local_today,
        )

    # --- Normalize Data if User Specified, otherwise graph actual asset price ---
    if is_norm:
        chart_data = normalize_prices(filtered_data)
    else:
        chart_data = filtered_data.copy()

    chart = build_comparison_chart(chart_data, is_norm, days_back)

status_ph.empty()   # Clear and completely remove status update box

chart_ph.altair_chart(chart, width="stretch")

st.caption(f"**Last updated:** {datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')} {local_tz}")
st.caption(f"**Requested date range:** {start_date.isoformat()} to {end_date.isoformat()}")
