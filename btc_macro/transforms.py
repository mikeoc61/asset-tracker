"""Pure data transformations used by the Streamlit dashboard."""

from datetime import date
from typing import Union

import pandas as pd


def prepare_price_data(
    data: Union[pd.DataFrame, pd.Series],
    selected_assets: list[str],
    start_date: date,
) -> tuple[pd.DataFrame, list[str]]:
    """Align downloaded prices and remove assets with no usable observations."""
    combined = pd.DataFrame(data).ffill()
    combined.index = pd.to_datetime(combined.index)
    combined = combined[combined.index >= pd.Timestamp(start_date)]
    filtered = combined.loc[:, selected_assets].copy()

    all_nan_assets = filtered.columns[filtered.isna().all()].tolist()
    if all_nan_assets:
        filtered = filtered.drop(columns=all_nan_assets)

    return filtered, all_nan_assets


def normalize_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Express each asset as percentage change from its first valid value."""
    baseline_values = pd.Series(index=prices.columns, dtype="float64")

    for column in prices.columns:
        first_index = prices[column].first_valid_index()
        if first_index is not None:
            baseline_values[column] = prices.at[first_index, column]

    baseline_values = baseline_values.replace(0, pd.NA)
    return (prices.divide(baseline_values, axis=1) - 1) * 100


def to_chart_frame(prices: pd.DataFrame) -> pd.DataFrame:
    """Convert wide price data into the long format expected by Altair."""
    chart_data = prices.copy()
    chart_data.index = pd.to_datetime(chart_data.index)
    chart_data.index.name = "Date"
    return chart_data.reset_index().melt(
        id_vars="Date",
        var_name="Asset",
        value_name="Value",
    )
