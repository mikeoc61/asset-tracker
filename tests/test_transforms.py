import unittest
from datetime import date

import pandas as pd
from pandas.testing import assert_frame_equal

from btc_macro.transforms import calculate_sma, normalize_prices, prepare_price_data, to_chart_frame


class MovingAverageTests(unittest.TestCase):
    def test_counts_actual_closes_and_excludes_unfinished_today(self):
        dates = pd.date_range("2024-01-01", periods=400)
        prices = pd.DataFrame({"BTC": range(1, 401)}, index=dates, dtype=float)
        sessions = dates[dates.dayofweek < 5]
        prices["SPY"] = pd.Series(range(1, len(sessions) + 1), index=sessions, dtype=float)
        prices["NEW"] = float("nan")
        prices.loc[dates[-199:], "NEW"] = 42.0
        original = prices.copy()
        result = calculate_sma(prices, dates[-1].date())
        self.assertNotIn(dates[-1], result.index)
        self.assertTrue(pd.isna(result.loc[dates[198], "BTC"]))
        self.assertEqual(result.loc[dates[199], "BTC"], 100.5)
        self.assertTrue(pd.isna(result.loc[sessions[198], "SPY"]))
        self.assertEqual(result.loc[sessions[199], "SPY"], 100.5)
        self.assertTrue(result["NEW"].isna().all())
        saturday = result.index[(result.index.dayofweek == 5) & (result.index > sessions[200])][0]
        self.assertEqual(result.loc[saturday, "SPY"], result.loc[saturday - pd.Timedelta(days=1), "SPY"])
        assert_frame_equal(prices, original)


class PreparePriceDataTests(unittest.TestCase):
    def test_custom_range_excludes_later_prices_and_normalizes_within_range(self):
        raw = pd.DataFrame(
            {"SPY": [80.0, 100.0, 110.0, 900.0]},
            index=pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]),
        )
        original = raw.copy()

        prepared, removed = prepare_price_data(
            raw, ["SPY"], date(2025, 1, 2), date(2025, 1, 3),
        )
        normalized = normalize_prices(prepared)

        self.assertEqual(removed, [])
        self.assertEqual(prepared["SPY"].tolist(), [100.0, 110.0])
        self.assertAlmostEqual(normalized["SPY"].iloc[0], 0.0)
        self.assertAlmostEqual(normalized["SPY"].iloc[-1], 10.0)
        assert_frame_equal(raw, original)

    def test_asset_with_data_only_after_end_is_removed(self):
        raw = pd.DataFrame(
            {"SPY": [100.0, 110.0], "NEW": [None, 200.0]},
            index=pd.to_datetime(["2025-01-02", "2025-01-03"]),
        )

        prepared, removed = prepare_price_data(
            raw, ["SPY", "NEW"], date(2025, 1, 2), date(2025, 1, 2),
        )

        self.assertEqual(removed, ["NEW"])
        self.assertEqual(prepared.columns.tolist(), ["SPY"])
        self.assertEqual(prepared["SPY"].tolist(), [100.0])

    def test_crypto_weekend_start_keeps_equity_baseline_on_first_trading_day(self):
        raw = pd.DataFrame(
            {"SPY": [None, None, 100.0, 110.0], "BTC-USD": [200.0, 220.0, 240.0, 260.0]},
            index=pd.to_datetime(["2026-09-19", "2026-09-20", "2026-09-21", "2026-09-22"]),
        )
        prepared, removed = prepare_price_data(raw, ["SPY", "BTC-USD"], date(2026, 9, 19))
        normalized = normalize_prices(prepared)

        self.assertEqual(removed, [])
        self.assertEqual(len(prepared), 4)
        self.assertTrue(normalized["SPY"].iloc[:2].isna().all())
        self.assertAlmostEqual(normalized["SPY"].iloc[-1], 10.0)
        self.assertAlmostEqual(normalized["BTC-USD"].iloc[-1], 30.0)

    def test_filters_dates_forward_fills_and_removes_empty_assets(self):
        raw = pd.DataFrame(
            {
                "SPY": [99.0, 100.0, None],
                "BTC-USD": [None, 50.0, 55.0],
                "MISSING": [None, None, None],
            },
            index=["2025-01-01", "2025-01-02", "2025-01-03"],
        )

        result, removed = prepare_price_data(
            raw,
            ["SPY", "BTC-USD", "MISSING"],
            date(2025, 1, 2),
        )

        expected = pd.DataFrame(
            {
                "SPY": [100.0, 100.0],
                "BTC-USD": [50.0, 55.0],
            },
            index=pd.to_datetime(["2025-01-02", "2025-01-03"]),
        )
        assert_frame_equal(result, expected, check_freq=False)
        self.assertEqual(removed, ["MISSING"])


class NormalizePricesTests(unittest.TestCase):
    def test_uses_each_assets_first_valid_value(self):
        prices = pd.DataFrame(
            {
                "SPY": [100.0, 110.0, 90.0],
                "BTC-USD": [None, 200.0, 300.0],
            }
        )

        result = normalize_prices(prices)

        expected = pd.DataFrame(
            {
                "SPY": [0.0, 10.0, -10.0],
                "BTC-USD": [None, 0.0, 50.0],
            }
        )
        assert_frame_equal(result, expected)

    def test_zero_baseline_does_not_produce_infinity(self):
        result = normalize_prices(pd.DataFrame({"ZERO": [0.0, 10.0]}))

        self.assertTrue(result["ZERO"].isna().all())


class ChartFrameTests(unittest.TestCase):
    def test_converts_prices_to_altair_long_format(self):
        prices = pd.DataFrame(
            {"SPY": [100.0], "BTC-USD": [200.0]},
            index=["2025-01-02"],
        )

        result = to_chart_frame(prices)

        self.assertEqual(result.columns.tolist(), ["Date", "Asset", "Value"])
        self.assertEqual(result["Asset"].tolist(), ["SPY", "BTC-USD"])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["Date"]))


if __name__ == "__main__":
    unittest.main()
