"""
BTC-Index Dashboard

This Streamlit app visualizes the relationship between Bitcoin (BTC) and key Market Index indicators
such as the S&P 500 (SPY), and Nasdaq-100 (QQQ). It allows users to explore 
price trends, correlations, and normalized percentage changes over customizable time ranges.

Features:
- Interactive chart with optional normalization (percent change from baseline)
- Sidebar toggles to include/exclude individual tickers
- Date range selector: 1 Week, 3 Months, 6 Months, 1 Year, Year-To-Date (YTD)

This tool helps visualize how BTC price movements align or diverge from traditional assets.

Reference:
- https://medium.com/@kasperjuunge/yfinance-10-ways-to-get-stock-data-with-python-6677f49e8282
"""

from datetime import date, timedelta, datetime
import time
import contextlib
import io
import re

import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
import pandas_market_calendars as mcal
import tzlocal
# import requests

# Get local timezone automatically
local_tz = tzlocal.get_localzone()

# Get *now* in your local timezone, and strip to date
local_today = datetime.now(local_tz).date()

# --- Set Page layout and titles ---
st.set_page_config(layout="wide")
st.title("📈 Asset Comparison")

# --- User Selected Options. Must be valid Ticker Symbol ---
tickers = ["SPY", "EFA", "IWM", "QQQ", "STRK", "NVDA", "APPL",
           "DX-Y.NYB", "GC=F", "SI=F", "HG=F",
           "BTC-USD", "ETH-USD", "SOL-USD"
           ]
default_tickers = ["SPY", "IWM", "EFA", "QQQ"]

# --- Session_State initialization to establish stable defaults ---
def init_state():
    st.session_state.setdefault("yf_ok", False)
    st.session_state.setdefault("applied_params", None)   # dict of last-applied settings
    st.session_state.setdefault("ticker_list", tickers.copy())
    st.session_state.setdefault("selected_assets", default_tickers.copy())
    st.session_state.setdefault("user_input", "")
    st.session_state.setdefault("add_ticker_error", "")
    st.session_state.setdefault("add_ticker_error_expires", 0.0)

init_state()

# Time range options specified in days
range_options = {
    "1 Week": 7,
    "1 Month": 31,
    "3 Months": 93,
    "6 Months": 182,
    "YTD": (local_today - date(local_today.year, 1, 1)).days,
    "1 Year": 365,
    "3 Years": (365*3),
    "5 Years": (365*5)
}

# --- Test for connection and / or rate limiting issues ---
def ensure_yfinance_once(test_ticker="SPY"):
    ''' Test for connection and / or rate limiting issues '''
    if st.session_state.get("yf_ok"):
        return  # already passed once this session

    try:
        df = yf.download(test_ticker, period="5d", progress=False)
        if df.empty:
            st.error("No data from Yahoo Finance. Possible rate limiting. Please try again later.")
            st.stop()
    except Exception as e:
        st.error(f"Data connection error: {e}")
        st.stop()

    st.session_state.yf_ok = True  # latch success

# --- Validate Ticker Symbol ---
def is_valid_ticker(symbol):
    ''' Make a minimal request to validate ticker is valid '''
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            df = yf.download(symbol, period="5d", progress=False)
        return not df.empty
    except Exception:
        return False

# --- Fetch Ticker Price Data ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_yf_data(tickers_key: tuple[str, ...], starting_date: str):
    """Return closing prices for tickers starting at starting_date (YYYY-MM-DD)."""
    tickers_list = list(tickers_key)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            close = yf.download(tickers_list, start=starting_date, progress=False)["Close"]

        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers_list[0])

        return close
    except Exception as e:
        raise RuntimeError(str(e)) from e

# --- Start Date Adjustment ---
def adjust_for_non_trading_day(orig_date):
    '''
    Adjust start start date to next trading day if otherwise starts on a US holiday
    Important so that data series always starts with an actual value
    '''
    nyse = mcal.get_calendar("NYSE")
    # Generate valid trading days from start_date onward
    trading_days = nyse.valid_days(
        start_date=orig_date.strftime("%Y-%m-%d"),
        end_date=(date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    )
    return trading_days[0].date()

def validate_assets(assets):
    """
    Validate selected tickers before fetching data. Stops execution if any ticker is invalid.
    """
    invalid = []

    for ticker in assets:
        if not is_valid_ticker(ticker):
            invalid.append(ticker)
        time.sleep(0.5)  # rate-limit API calls only

    if invalid:
        st.error(
            f"Invalid ticker(s): {', '.join(invalid)}. "
            "Please correct your selection."
        )
        st.stop()

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
    selected_range = st.selectbox("Time Range", options=list(range_options.keys()))
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

    # --- Date Calculations based on user selected range option ---
    days_back = range_options[selected_range]
    start_date = date.today() - timedelta(days=days_back)
    adj_date = adjust_for_non_trading_day(start_date)

    # # --- Test for connection issues, on first pass ---
    status.write("Checking Yahoo Finance connectivity")
    ensure_yfinance_once("SPY")

    # --- Validate selected tickers ---
    status.write(f"Validating Assets: {', '.join(selected_assets)}")
    validate_assets(selected_assets)

    # --- Data Download (only selected tickers) ---
    status.write("Downloading price data")
    tickers_key = tuple(sorted(selected_assets))
    start_key = pd.Timestamp(adj_date).strftime("%Y-%m-%d")
    
    try:
        data = get_yf_data(tickers_key, start_key)
    except RuntimeError as e:
        st.error(f"Download failed: {e}")
        st.stop()

    # Forward-fill missing values for non-trading days
    # Combine into one DataFrame and trim rows before adjusted start_date
    # Filter by user-selected assets. Include assets with data gaps
    combined = pd.DataFrame(data).ffill()
    combined = combined[combined.index >= pd.to_datetime(start_date)]
    filtered_data = combined[selected_assets]

    # --- Make sure the DataFrame index is a DatetimeIndex (safety check) ---
    if not isinstance(filtered_data.index, pd.DatetimeIndex):
        filtered_data.index = pd.to_datetime(filtered_data.index)

    # --- Drop assets with no data in selected range ---
    all_nan_assets = filtered_data.columns[filtered_data.isna().all()].tolist()

    if all_nan_assets:
        # Remove them from the DataFrame
        filtered_data = filtered_data.drop(columns=all_nan_assets)

        # Optional: warn user (non-fatal)
        st.warning(
            f"Removed asset(s) with no data in selected range: {', '.join(all_nan_assets)}"
        )

    # Final guard: stop if nothing remains
    if filtered_data.empty:
        st.error("No valid price data available for the selected assets and date range.")
        st.stop()

    # --- Looks like we're good to proceed so sync selected_assets with filtered data ---
    selected_assets = filtered_data.columns.tolist()

    # --- Patch last row with real-time data for 24/7 tickers like BTC-USD ---
    for t in selected_assets:
        if "-USD" in t:
            try:
                realtime_price = yf.Ticker(t).info.get("regularMarketPrice")
                if pd.notna(realtime_price):
                    # If last known data date is before today, append new row
                    if filtered_data.index[-1].date() < local_today:
                        new_row = pd.DataFrame({t: realtime_price}, index=[pd.Timestamp(local_today)])
                        filtered_data = pd.concat([filtered_data, new_row])
                    else:
                        # If the row for today exists, just update the price
                        filtered_data.loc[filtered_data.index[-1], t] = realtime_price
            except Exception as e:
                print(f"Error updating {t} with real-time price: {e}")

    # --- Normalize Data if User Specified, otherwise graph actual asset price ---
    if is_norm:
        # first non-NaN per column; returns NaN if the entire column is NaN
        baseline = filtered_data.apply(pd.Series.first_valid_index)
        baseline_values = pd.Series(index=filtered_data.columns, dtype="float64")

        for c in filtered_data.columns:
            idx = baseline[c]
            baseline_values[c] = filtered_data.loc[idx, c] if idx is not None else float("nan")

        # Avoid division by zero; keep NaN columns as NaN
        baseline_values = baseline_values.replace(0, pd.NA)

        chart_data = (filtered_data.divide(baseline_values, axis=1) - 1) * 100
    else:
        chart_data = filtered_data.copy()

    # --- Construct Altair Chart ---
    chart_data = chart_data.copy()
    chart_data.index = pd.to_datetime(chart_data.index)
    chart_data.index.name = "Date"
    chart_df = chart_data.reset_index().melt(id_vars="Date", var_name="Asset", value_name="Value")

    # Hover highlight (visual only)
    hover_sel = alt.selection_point(
        fields=["Asset"],
        on="mouseover",
        clear="mouseout",
    )

    # Click selection (NOT YET IMPLEMENTED)
    click_sel = alt.selection_point(
        name="asset_click",
        fields=["Asset"],
        on="click",
        clear="dblclick",   # double-click clears selection
    )

    Y_MARGIN_PCT = 0.15  # 10–20% recommended

    Y_DOMAIN = None
    if is_norm:
        vals = pd.to_numeric(chart_df["Value"], errors="coerce").dropna()
        if not vals.empty:
            y_min = float(vals.min())
            y_max = float(vals.max())

            # Avoid zero-range edge case
            pad = (y_max - y_min) * Y_MARGIN_PCT if y_max != y_min else max(abs(y_max) * Y_MARGIN_PCT, 1.0)

            Y_DOMAIN = [y_min - pad, y_max + pad]

    y_axis = alt.Y(
        "Value:Q",
        title="% Change" if is_norm else "Price (USD)",
        scale=alt.Scale(domain=Y_DOMAIN, zero=False, nice=True) if Y_DOMAIN else alt.Scale(zero=False, nice=True),
        axis=alt.Axis(
            orient="right",
            labelColor="orange",
            titleColor="orange",
            labelAlign="center"
        )
    )

    value_tooltip = alt.Tooltip(
        "Value:Q",
        title="% Change" if is_norm else "Price (USD)",
        format=".2f" if is_norm else ",.2f"
    )

    main_chart = (
    alt.Chart(chart_df)
    .mark_line()
    .encode(
        x=alt.X("Date:T", axis=alt.Axis(labelColor="orange", labelAlign="center")),
        y=y_axis,
        color="Asset:N",
        opacity=alt.condition(hover_sel, alt.value(1.0), alt.value(0.25)),
        strokeWidth=alt.condition(hover_sel, alt.value(3), alt.value(1.5)),
        tooltip=[
            alt.Tooltip("Date:T", title="Date"),
            alt.Tooltip("Asset:N", title="Ticker"),
            value_tooltip
        ],
    )
    .add_params(hover_sel, click_sel)
    )

    def get_time_boundaries(dates, freq):
        '''Draw Vertical lines for month or year boundaries'''
        df = pd.DataFrame({"Date": pd.to_datetime(dates)})
        df["Boundary"] = df["Date"].dt.to_period(freq)
        df["Label"] = df["Date"].dt.strftime("%b %Y") if freq == "M" else df["Date"].dt.strftime("%Y")
        return df.drop_duplicates("Boundary")[["Date", "Label"]]

    # --- Adjust hash boundaries based on date range ---
    F_VALUE = "M" if (days_back <= 365) else "Y"    # Use "M" for monthly or "Y" for yearly
    boundaries_df = get_time_boundaries(chart_df["Date"], freq=F_VALUE)

    # --- define verticle hash marks ---
    rules = alt.Chart(boundaries_df).mark_rule(
        color="gray", strokeDash=[3, 3]
    ).encode(
        x="Date:T"
    )

    layers = [main_chart, rules]

    # --- Add emphasis to line at Y = 0 on the chart when using Normalized view ---
    if is_norm:
        baseline_rule = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
            strokeDash=[4, 4],
            color="orange",
        ).encode(y="y:Q")
        layers.append(baseline_rule)

status_ph.empty()   # Clear and completely remove status update box

chart = alt.layer(*layers).properties(width=800, height=600).interactive()

chart_ph.altair_chart(chart, width="stretch")

st.caption(f"**Last updated:** {datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')} {local_tz}")
st.caption(f"**Data range:** {adj_date.strftime('%Y-%m-%d')} to {date.today().strftime('%Y-%m-%d')}")