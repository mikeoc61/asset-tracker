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


def resolve_date_range(
    selected_range: str,
    today: date,
    custom_start: Optional[date] = None,
    custom_end: Optional[date] = None,
) -> tuple[date, date]:
    """Return inclusive calendar bounds, validating user-supplied dates."""
    if selected_range != "Custom":
        return range_start(selected_range, today), today

    if custom_start is None or custom_end is None:
        raise ValueError("Choose both a start date and an end date.")
    if custom_start > custom_end:
        raise ValueError("Start date must be on or before end date.")
    if custom_end > today:
        raise ValueError("End date cannot be later than today.")

    return custom_start, custom_end
