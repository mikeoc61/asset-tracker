"""Yahoo Finance access and response-normalization helpers."""

import contextlib
import io
from datetime import date, timedelta
from typing import Callable, Optional

import pandas as pd
import yfinance as yf


def ticker_has_recent_data(
    symbol: str,
    downloader: Optional[Callable] = None,
) -> bool:
    """Return whether Yahoo Finance has recent data for a ticker symbol."""
    download = downloader or yf.download
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            data = download(symbol, period="5d", progress=False)
        return not data.empty
    except Exception:
        return False


def download_close_prices(
    tickers: list[str],
    starting_date: str,
    downloader: Optional[Callable] = None,
    *,
    ending_date: Optional[str] = None,
) -> pd.DataFrame:
    """Download closing prices with an optional inclusive end date."""
    download = downloader or yf.download
    try:
        download_options = {"start": starting_date, "progress": False}
        if ending_date is not None:
            # Yahoo's end parameter is exclusive; dashboard dates are inclusive.
            download_options["end"] = (
                date.fromisoformat(ending_date) + timedelta(days=1)
            ).isoformat()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            downloaded = download(tickers, **download_options)

        if downloaded.empty:
            raise RuntimeError(
                "Yahoo Finance returned no data for the selected assets and date range. "
                "Try another range; the service may also be temporarily unavailable or rate limited."
            )

        return extract_close_prices(downloaded, tickers)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def fetch_current_prices(
    tickers: list[str],
    ticker_factory: Optional[Callable] = None,
) -> dict[str, float]:
    """Fetch current prices, omitting tickers whose lookup fails."""
    factory = ticker_factory or yf.Ticker
    prices = {}

    for ticker in tickers:
        try:
            price = factory(ticker).info.get("regularMarketPrice")
            if pd.notna(price):
                prices[ticker] = float(price)
        except Exception:
            continue

    return prices


def apply_current_prices(
    prices: pd.DataFrame,
    current_prices: dict[str, float],
    as_of: date,
) -> pd.DataFrame:
    """Apply current quotes to one shared as-of row without mutating input."""
    result = prices.copy()
    applicable = {
        ticker: value
        for ticker, value in current_prices.items()
        if ticker in result.columns and pd.notna(value)
    }

    if result.empty or not applicable:
        return result

    if result.index[-1].date() < as_of:
        target_index = pd.Timestamp(as_of)
        new_row = pd.DataFrame(index=[target_index], columns=result.columns, dtype="float64")
        result = pd.concat([result, new_row])
    else:
        target_index = result.index[-1]

    for ticker, value in applicable.items():
        result.at[target_index, ticker] = value

    return result


def extract_close_prices(
    downloaded: pd.DataFrame,
    tickers: list[str],
) -> pd.DataFrame:
    """Return closing prices with one consistently named column per ticker."""
    if isinstance(downloaded.columns, pd.MultiIndex):
        if "Close" not in downloaded.columns.get_level_values(0):
            raise ValueError("Yahoo Finance response did not include closing prices.")
        close = downloaded["Close"]
    else:
        if "Close" not in downloaded.columns:
            raise ValueError("Yahoo Finance response did not include closing prices.")
        close = downloaded["Close"]

    if isinstance(close, pd.Series):
        if len(tickers) != 1:
            raise ValueError("Yahoo Finance returned an unexpected price-data shape.")
        close = close.to_frame(name=tickers[0])

    # Missing or invalid symbols become all-NaN columns and are handled by the
    # shared preparation step, while valid columns retain the requested order.
    return close.reindex(columns=tickers)
