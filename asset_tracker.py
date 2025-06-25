"""
BTC-Index Dashboard

This Streamlit app visualizes the relationship between Bitcoin (BTC) and key Market Index indicators
such as the S&P 500 (SPY), and Nasdaq-100 (QQQ). It allows users to explore 
price trends, correlations, and normalized percentage changes over customizable time ranges.

Features:
- Interactive chart with optional normalization (percent change from baseline)
- Sidebar toggles to include/exclude individual tickers
- Date range selector: 1 Week, 3 Months, 6 Months, 1 Year, Year-To-Date (YTD)

This tool helps visualize how BTC price movements align or diverge from traditional macroeconomic assets.

Reference:
- https://medium.com/@kasperjuunge/yfinance-10-ways-to-get-stock-data-with-python-6677f49e8282
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import date, timedelta, datetime
import pandas_market_calendars as mcal
import tzlocal
import requests
import time

# Get local timezone automatically
local_tz = tzlocal.get_localzone()

# Get *now* in your local timezone, and strip to date
local_today = datetime.now(local_tz).date()

# --- Set Page layout and titles ---
st.set_page_config(layout="wide")
st.title("📈 Asset Comparison")
st.caption(f"Last Updated: {datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')} {local_tz}")

# --- Session state flag for update control ---
if "update_graph" not in st.session_state:
    st.session_state.update_graph = False

# --- User Selected Options. Must be valid Ticker Symbol ---
tickers = ["SPY", "BTC-USD", "FBTC", "ETH-USD", "DX-Y.NYB", "GC=F", "SOL-USD", "EFA", "QQQ", "STRK", "FDGRX", "FBAKX"]
default_tickers = ["SPY", "BTC-USD", "EFA"]

# --- Test for connection and / or rate limiting issues ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def check_yfinance_connection():
    test_ticker = tickers[0]
    today = date.today()
    try:
        test_data = yf.download(test_ticker, start=today - timedelta(days=1), end=today, progress=False)
        if test_data.empty:
            st.error("No data from Yahoo Finance. Possible rate limiting or network issues. Please try again later.")
            st.stop()
    except (requests.exceptions.RequestException, Exception) as e:
        st.error(f"Data connection error: {e}")
        st.stop()

# --- Validate Ticker Symbol ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def is_valid_ticker(ticker):
    try:
        info = yf.Ticker(ticker).info
        return bool(info) and "regularMarketPrice" in info
    except Exception as e:
        st.error(f"{e}")
        return False
    
# --- Fetch Ticker Price Data ---
# Call Yahoo Finance with list of provided tickers. Cache data for specified ttl (3600 = 1 hour)
@st.cache_data(ttl=3600)
def get_data(tickers, start_date):
    try: 
        data = yf.download(tickers, start=start_date, progress=False)["Close"]
        return data
    except Exception as e:
        st.error(f"{e}")
        st.stop()
    
# Adjust return start date to next trading day if otherwise starts on a US holiday
# Important so that data series always starts with an actual value
def adjust_for_non_trading_day(start_date):
    nyse = mcal.get_calendar("NYSE")
    # Generate valid trading days from start_date onward
    trading_days = nyse.valid_days(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=(date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        # end_date=(date_local + timedelta(days=1)).strftime("%Y-%m-%d")
    )
    return trading_days[0].date()

# --- Validate selected tickers ---
# Warn users about tickers without valid price data and stop until deselected
def validate_assets(tickers):
    invalid_assets = []
    for ticker in tickers:
        if is_valid_ticker(ticker) == False:
            st.error(f"Invalid Ticker(s) detected: {', '.join(invalid_assets)}. Please correct your selection.")
            st.stop()
        else:
            time.sleep(1)

    if invalid_assets:
        st.error(f"Invalid Ticker(s) detected: {', '.join(invalid_assets)}. Please correct your selection.")
        st.stop()

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

# --- Create sidebar Widgets ---
with st.sidebar:
    view = st.radio("Select View", ["Price (USD)", "Normalized % Change"], index=1)
    selected_range = st.selectbox("Select Time Range", options=list(range_options.keys()))
    selected_assets = st.multiselect("Select Assets", options=list(tickers), default=default_tickers)

    user_ticker = st.text_input("User ticker", placeholder="e.g., TSLA")
    if user_ticker:
        user_ticker = user_ticker.strip().upper()
        selected_assets.append(user_ticker)
        selected_assets = list(set(selected_assets))  # De-duplicate nicely
   
    st.write("")
    update_clicked = st.button("🔄 Update Graph 🔄")

# --- Logic only runs if button pressed, button resets to False after each pass ---
if update_clicked:

    # --- Date Calculations based on user selected range option ---
    days_back = range_options[selected_range]
    start_date = date.today() - timedelta(days=days_back)
    adj_date = adjust_for_non_trading_day(start_date)

    # --- Test for connection issues ---
    check_yfinance_connection()

    # --- Validate selected tickers ---
    validate_assets(selected_assets)

    # --- Data Download (only selected tickers) ---
    if selected_assets:
        data = get_data(selected_assets, adj_date)
    else:
        st.warning("Please select at least one ticker.")
        st.stop()

    # Forward-fill missing values for non-trading days
    # Combine into one DataFrame and trim rows before adjusted start_date
    # Filter by user-selected assets. Include assets with data gaps
    combined = pd.DataFrame(data).ffill()
    combined = combined[combined.index >= pd.to_datetime(start_date)]
    filtered_data = combined[selected_assets]

    # --- Patch last row with real-time data for 24/7 tickers like BTC-USD ---
    for ticker in selected_assets:
        if "-USD" in ticker:
            try:
                realtime_price = yf.Ticker(ticker).info.get("regularMarketPrice")
                if pd.notna(realtime_price):
                    # Make sure the DataFrame index is a DatetimeIndex (safety check)
                    if not isinstance(filtered_data.index, pd.DatetimeIndex):
                        filtered_data.index = pd.to_datetime(filtered_data.index)

                    # If last known data date is before today, append new row
                    if filtered_data.index[-1].date() < local_today:
                        new_row = pd.DataFrame({ticker: realtime_price}, index=[pd.Timestamp(local_today)])
                        filtered_data = pd.concat([filtered_data, new_row])
                    else:
                        # If the row for today exists, just update the price
                        filtered_data.loc[filtered_data.index[-1], ticker] = realtime_price
            except Exception as e:
                print(f"Error updating {ticker} with real-time price: {e}")

    # print(filtered_data)

    # --- Normalize Data ---
    if view == "Normalized % Change":
        baseline = filtered_data.apply(lambda col: col.loc[col.first_valid_index()])
        baseline = baseline.replace(0, 1e-8)
        chart_data = (filtered_data / baseline - 1) * 100
    else:
        chart_data = filtered_data.copy()

    # print(chart_data)

    # --- Altair Chart ---
    chart_df = chart_data.reset_index().melt(id_vars="Date", var_name="Asset", value_name="Value")

    y_axis = alt.Y(
        "Value:Q",
        title="% Change" if view == "Normalized % Change" else "Price (USD)",
    )

    chart = alt.Chart(chart_df).mark_line().encode(
        x="Date:T",
        y=y_axis,
        color="Asset:N"
    ).properties(width=800, height=600).interactive()

    st.altair_chart(chart, use_container_width=True)

    # Reset update flag
    # st.session_state.update_graph = False

# --- Latest Prices ---
# st.subheader("Latest Prices")
# latest = data.iloc[-1]
# st.write(latest.map("${:,.2f}".format))