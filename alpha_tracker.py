import pandas as pd
import time
import os
from datetime import date, timedelta
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.cryptocurrencies import CryptoCurrencies
from dotenv import load_dotenv

load_dotenv()
ALPHA_VANTAGE_API_KEY=os.getenv("ALPHA_VANTAGE_API_KEY") 
                                
# Identify crypto tickers by the presence of a dash
def is_crypto(ticker):
    return "-" in ticker

def fetch_crypto(key, ticker):
    symbol, market = ticker.split("-")
    cc = CryptoCurrencies(key=key, output_format="pandas")
    df, _ = cc.get_digital_currency_daily(symbol=symbol, market=market)
    # Select close column and rename to ticker (e.g., 'BTC-USD')
    df = df[["4. close"]].rename(columns={"4. close": ticker})
    return df

def fetch_equity(key, ticker):
    ts = TimeSeries(key=key, output_format="pandas")
    df, _ = ts.get_daily(symbol=ticker, outputsize='compact')   # specify outputsize='full' for more than last 100 data points
    # Select close column and rename to ticker (e.g., 'SPY')
    df = df[["4. close"]].rename(columns={"4. close": ticker})
    return df

def fetch_alpha_vantage_data(key, tickers, start_date):
    all_data = []
    start_date = pd.to_datetime(start_date)

    for i, ticker in enumerate(tickers):
        try:
            df = fetch_crypto(key, ticker) if is_crypto(ticker) else fetch_equity(key, ticker)

            # Normalize index and sort
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()

            # only include rows with dates on or after start_date
            df = df[df.index >= start_date]
            all_data.append(df)

        except Exception as e:
            print(f"Error fetching {ticker}: {e}")

        # Respect API rate limit
        if i < len(tickers) - 1:
            time.sleep(2)

    if not all_data:
        return pd.DataFrame()

    combined = pd.concat(all_data, axis=1)
    return combined

if __name__ == "__main__":
    load_dotenv()
    key=os.getenv("ALPHA_VANTAGE_API_KEY")
    
    tickers = ["SPY", "BTC-USD", "FBTC", "ETH-USD", "SOL-USD", "EFA", "QQQ", "STRK", "FDGRX", "FBAKX"]

    start_date = date.today() - timedelta(days=7)
    print (fetch_alpha_vantage_data(key, tickers, start_date))