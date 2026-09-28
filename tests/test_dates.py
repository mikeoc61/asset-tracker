import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from btc_macro.dates import range_start, resolve_date_range


class DateRangeTests(unittest.TestCase):
    def test_ytd_starts_on_january_first_including_on_new_years_day(self):
        for today in (date(2026, 1, 1), date(2026, 12, 31)):
            with self.subTest(today=today):
                self.assertEqual(range_start("YTD", today), date(2026, 1, 1))

    def test_weekend_start_is_not_shifted_to_monday(self):
        self.assertEqual(range_start("1 Week", date(2026, 9, 27)), date(2026, 9, 20))

    def test_week_range_crosses_year_boundary(self):
        self.assertEqual(range_start("1 Week", date(2026, 1, 2)), date(2025, 12, 26))

    def test_ytd_uses_supplied_timezone_date_at_midnight_boundary(self):
        instant = datetime(2026, 1, 1, 1, tzinfo=ZoneInfo("UTC"))
        today = instant.astimezone(ZoneInfo("Pacific/Honolulu")).date()
        self.assertEqual(range_start("YTD", today), date(2025, 1, 1))

    def test_preset_range_ends_today(self):
        today = date(2026, 9, 27)
        self.assertEqual(
            resolve_date_range("1 Month", today),
            (date(2026, 8, 27), today),
        )

    def test_custom_range_keeps_weekends_and_crosses_year_boundary(self):
        bounds = (date(2025, 12, 27), date(2026, 1, 3))
        self.assertEqual(resolve_date_range("Custom", date(2026, 9, 27), *bounds), bounds)

    def test_custom_range_accepts_one_day_and_today(self):
        today = date(2026, 9, 27)
        self.assertEqual(resolve_date_range("Custom", today, today, today), (today, today))

    def test_custom_range_requires_both_dates(self):
        today = date(2026, 9, 27)
        for bounds in ((None, today), (today, None), (None, None)):
            with self.subTest(bounds=bounds), self.assertRaisesRegex(ValueError, "both"):
                resolve_date_range("Custom", today, *bounds)

    def test_custom_range_rejects_reversed_dates(self):
        with self.assertRaisesRegex(ValueError, "on or before"):
            resolve_date_range("Custom", date(2026, 9, 27), date(2026, 9, 20), date(2026, 9, 19))

    def test_custom_range_rejects_future_end(self):
        with self.assertRaisesRegex(ValueError, "later than today"):
            resolve_date_range("Custom", date(2026, 9, 27), date(2026, 9, 20), date(2026, 9, 28))


if __name__ == "__main__":
    unittest.main()
