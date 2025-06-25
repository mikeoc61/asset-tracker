from twelvedata import TDClient
import pandas as pd
import os
from datetime import date, timedelta
from dotenv import load_dotenv

# Initialize Twelve Data client
td = TDClient(apikey=os.getenv("TWELVE_DATA_API_KEY"))

# Normalize ticker to Twelve Data format and track mapping
def normalize_tickers(tickers):
    normalized_map = {}
    for t in tickers:
        if "-" in t and t.upper().endswith("USD"):
            base, quote = t.upper().split("-")
            normalized = f"{base}/{quote}"
        else:
            normalized = t
        normalized_map[t] = normalized
    return normalized_map

def convert_batch_df(df, ticker_map):
    """Convert Twelve Data's multi-index DataFrame into a flat DataFrame of close prices."""
    all_data = []

    for user_ticker, td_ticker in ticker_map.items():
        try:
            symbol_df = df.loc[td_ticker]
            close_series = symbol_df[["close"]].copy()
            close_series = close_series.rename(columns={"close": user_ticker})
            all_data.append(close_series)
        except KeyError:
            print(f"Missing data for {user_ticker}")

    if all_data:
        return pd.concat(all_data, axis=1).sort_index()
    else:
        return pd.DataFrame()
    
def fetch_twelvedata_batch_closes(key, tickers, start_date):
    # Initialize Twelve Data client
    td = TDClient(key)
    ticker_map = normalize_tickers(tickers)
    symbols = ",".join(set(ticker_map.values()))
    end_date = date.today().isoformat()

    try:
        ts = td.time_series(
            symbol=symbols,
            interval="1day",
            start_date=start_date,
            end_date=end_date
        )
        df = ts.as_pandas()
        df = convert_batch_df(df, ticker_map)
        return df
    except Exception as e:
            print(f"Error fetching {symbols}: {e}")

if __name__ == "__main__":
    load_dotenv()
    key=os.getenv("TWELVE_DATA_API_KEY")

    tickers = ["SPY", "BTC-USD"]

    start_date = (date.today() - timedelta(days=7)).isoformat()

    print(start_date)

    df = fetch_twelvedata_batch_closes(key, tickers, start_date)
    print(df)