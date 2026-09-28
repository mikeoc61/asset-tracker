import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from btc_macro.dates import range_start


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


if __name__ == "__main__":
    unittest.main()
