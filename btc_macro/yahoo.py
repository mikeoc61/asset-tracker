"""Helpers for normalizing Yahoo Finance download responses."""

import pandas as pd


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
