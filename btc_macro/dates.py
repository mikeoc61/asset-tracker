"""Calendar-date ranges shared by the dashboard."""

from datetime import date, timedelta
from typing import Optional


RANGE_OPTIONS: dict[str, Optional[int]] = {
    "1 Week": 7,
    "1 Month": 31,
    "3 Months": 93,
    "6 Months": 182,
    "YTD": None,
    "1 Year": 365,
    "3 Years": 365 * 3,
    "5 Years": 365 * 5,
}


def range_start(selected_range: str, today: date) -> date:
    """Keep calendar starts intact; each asset supplies its own trading dates."""
    days = RANGE_OPTIONS[selected_range]
    if days is None:
        return date(today.year, 1, 1)
    return today - timedelta(days=days)
