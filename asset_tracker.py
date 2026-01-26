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

import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
import pandas_market_calendars as mcal
import tzlocal
import requests

# Get local timezone automatically
local_tz = tzlocal.get_localzone()

# Get *now* in your local timezone, and strip to date
local_today = datetime.now(local_tz).date()

# --- Set Page layout and titles ---
st.set_page_config(layout="wide")
st.title("📈 Asset Comparison")

# --- Session state flag for update control ---
if "update_graph" not in st.session_state:
    st.session_state.update_graph = False

# --- User Selected Options. Must be valid Ticker Symbol ---
tickers = ["SPY", "BTC-USD", "ETH-USD", "DX-Y.NYB", "GC=F", "SOL-USD", "EFA", "QQQ", "STRK"]
default_tickers = ["SPY", "BTC-USD", "EFA"]

# --- Initialize session state - first pass only ---
if "ticker_list" not in st.session_state:
    st.session_state.ticker_list = tickers.copy()
if "selected_assets" not in st.session_state:
    st.session_state.selected_assets = default_tickers.copy()
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "add_ticker_error" not in st.session_state:
    st.session_state.add_ticker_error = ""

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
@st.cache_data(ttl=3600)  # Cache for 1 hour
def check_yfinance_connection(test_ticker):
    '''Check to make sure we have basic functionality'''
    today = date.today()
    try:
        test_data = yf.download(test_ticker, start=today - timedelta(days=1), end=today, progress=False)
        if test_data.empty:
            st.error("No data from Yahoo Finance. Possible rate limiting. Please try again later.")
            st.stop()
    except (requests.exceptions.RequestException, Exception) as e:
        st.error(f"Data connection error: {e}")
        st.stop()

# --- Validate Ticker Symbol ---
def is_valid_ticker(symbol):
    '''Make a minimal request to validate ticker is valid'''
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            df = yf.download(symbol, period="5d", progress=False)
        return not df.empty
    except Exception:
        return False

# --- Fetch Ticker Price Data ---
@st.cache_data(ttl=3600)
def get_yf_data(tickers_list, starting_date):
    '''Query yahoo finance to provide cloding price data for a list of tickers'''
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            yf_data = yf.download(tickers_list, start=starting_date, progress=False)["Close"]
        return yf_data
    except Exception as e:
        st.error(f"{e}")
        st.stop()

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

def validate_assets(stocks):
    '''Warn users about tickers without valid price data'''
    for s in stocks:
        if not is_valid_ticker(s):
            st.error(f"Invalid Ticker: {s}. Please correct your selection.")
        time.sleep(1)

def add_ticker():
    '''Callback function adds user supplied ticker to multi-select list'''
    new_ticker = st.session_state.user_input.strip().upper()

    if not new_ticker:
        return

    if is_valid_ticker(new_ticker):
        if new_ticker not in st.session_state.ticker_list:
            st.session_state.ticker_list.append(new_ticker)

        # Preserve selected assets and append new one if not present
        current_selection = st.session_state.get("selected_assets", []).copy()
        if new_ticker not in current_selection:
            current_selection.append(new_ticker)
        st.session_state.selected_assets = current_selection  # Explicit reassign

        st.session_state.user_input = ""
        st.session_state.add_ticker_error = ""
        st.session_state.add_ticker_error_time = 0
    else:
        st.session_state.add_ticker_error = f"Sorry, {new_ticker} is not a valid ticker."
        # st.session_state.add_ticker_error_time = time.time()
        st.session_state.add_ticker_error_expires = time.time() + 2

# --- Create sidebar Widgets ---
with st.sidebar:
    view = st.radio("Select View", ["Price (USD)", "Normalized % Change"], index=1)
    selected_range = st.selectbox("Select Time Range", options=list(range_options.keys()))
    st.multiselect(
        "Select Assets", 
        options=list(st.session_state.ticker_list),
        key="selected_assets"   # <- lets Streamlit manage and persist selection
    )
    st.text_input("Add ticker", key="user_input", on_change=add_ticker, placeholder="e.g., TSLA")

    msg = st.session_state.get("add_ticker_error", "")
    expires = st.session_state.get("add_ticker_error_expires", 0)
    if msg and time.time() < expires:
        st.error(msg)

    for i in range (15):
        st.write("")

    left, mid, right = st.columns([1, 4, 1])
    with mid:
        update_clicked = st.button("🔄 Graph Results 🔄", use_container_width=True)

# Now that we have a final list of selected assets let's make a copy of the
# session state and use that going forward for simplicity
selected_assets = st.session_state.selected_assets.copy()

# --- Date Calculations based on user selected range option ---
days_back = range_options[selected_range]
start_date = date.today() - timedelta(days=days_back)
adj_date = adjust_for_non_trading_day(start_date)

# --- Test for connection issues ---
check_yfinance_connection("SPY")

# --- Logic only runs if button pressed, button resets to False after each pass ---
if update_clicked:

    # --- Validate selected tickers ---
    validate_assets(selected_assets)

    # --- Data Download (only selected tickers) ---
    if selected_assets:
        data = get_yf_data(selected_assets, adj_date)
    else:
        st.warning("Please select at least one ticker.")
        st.stop()

    # Forward-fill missing values for non-trading days
    # Combine into one DataFrame and trim rows before adjusted start_date
    # Filter by user-selected assets. Include assets with data gaps
    combined = pd.DataFrame(data).ffill()
    combined = combined[combined.index >= pd.to_datetime(start_date)]
    filtered_data = combined[selected_assets]

    # Make sure the DataFrame index is a DatetimeIndex (safety check)
    if not isinstance(filtered_data.index, pd.DatetimeIndex):
        filtered_data.index = pd.to_datetime(filtered_data.index)

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
    if view == "Normalized % Change":
        baseline = filtered_data.apply(lambda col: col.loc[col.first_valid_index()])
        baseline = baseline.replace(0, 1e-8)
        chart_data = (filtered_data / baseline - 1) * 100
    else:
        chart_data = filtered_data.copy()

    # --- Altair Chart ---
    chart_df = chart_data.reset_index().melt(id_vars="Date", var_name="Asset", value_name="Value")

    y_axis = alt.Y(
        "Value:Q",
        title="% Change" if view == "Normalized % Change" else "Price (USD)",
        axis=alt.Axis(
            orient="right",
            labelColor="orange",
            titleColor="orange",
            labelAlign="center"
        )
    )

    main_chart = alt.Chart(chart_df).mark_line().encode(
        x=alt.X(
        "Date:T",
        axis=alt.Axis(
            labelColor="orange",
            labelAlign="center"
            )),
        y=y_axis,
        color="Asset:N"
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

    # --- Add emphasis to line at Y = 0 on the chart ---
    baseline_rule = alt.Chart(
        pd.DataFrame({'y': [0]})
    ).mark_rule(
        strokeDash=[4,4], color='orange').encode(
        y='y:Q'
    )

    # --- Combine main chart and vertical line rules ---
    chart = (main_chart + rules + baseline_rule).properties(width=800, height=600).interactive()

    st.altair_chart(chart, width='stretch')

    st.caption(f"**Last updated:** {datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')} {local_tz}")
    st.caption(f"**Data range:** {adj_date.strftime('%Y-%m-%d')} to {date.today().strftime('%Y-%m-%d')}")

# --- Latest Prices ---
# st.subheader("Latest Prices")
# latest = data.iloc[-1]
# st.write(latest.map("${:,.2f}".format))
