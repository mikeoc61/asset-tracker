import unittest
from datetime import date

import pandas as pd
from pandas.testing import assert_frame_equal

from btc_macro.transforms import normalize_prices, prepare_price_data, to_chart_frame


class PreparePriceDataTests(unittest.TestCase):
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
