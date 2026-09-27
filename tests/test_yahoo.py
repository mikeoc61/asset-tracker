import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from btc_macro.yahoo import extract_close_prices


class ExtractClosePricesTests(unittest.TestCase):
    def test_extracts_multi_ticker_close_columns_in_requested_order(self):
        columns = pd.MultiIndex.from_product(
            [["Close", "Open"], ["BTC-USD", "SPY"]],
            names=["Price", "Ticker"],
        )
        downloaded = pd.DataFrame(
            [[200.0, 100.0, 190.0, 95.0]],
            columns=columns,
            index=pd.to_datetime(["2025-01-02"]),
        )

        result = extract_close_prices(downloaded, ["SPY", "BTC-USD"])

        expected = pd.DataFrame(
            {"SPY": [100.0], "BTC-USD": [200.0]},
            index=pd.to_datetime(["2025-01-02"]),
        )
        expected.columns.name = "Ticker"
        assert_frame_equal(result, expected)

    def test_normalizes_single_ticker_series(self):
        downloaded = pd.DataFrame(
            {"Close": [100.0, 101.0]},
            index=pd.to_datetime(["2025-01-02", "2025-01-03"]),
        )

        result = extract_close_prices(downloaded, ["SPY"])

        expected = pd.DataFrame(
            {"SPY": [100.0, 101.0]},
            index=pd.to_datetime(["2025-01-02", "2025-01-03"]),
        )
        assert_frame_equal(result, expected)

    def test_adds_nan_column_for_a_missing_ticker(self):
        columns = pd.MultiIndex.from_tuples(
            [("Close", "SPY")],
            names=["Price", "Ticker"],
        )
        downloaded = pd.DataFrame(
            [[100.0]],
            columns=columns,
            index=pd.to_datetime(["2025-01-02"]),
        )

        result = extract_close_prices(downloaded, ["SPY", "MISSING"])

        self.assertEqual(result.columns.tolist(), ["SPY", "MISSING"])
        self.assertTrue(result["MISSING"].isna().all())

    def test_rejects_response_without_close_prices(self):
        downloaded = pd.DataFrame({"Open": [100.0]})

        with self.assertRaisesRegex(ValueError, "closing prices"):
            extract_close_prices(downloaded, ["SPY"])


if __name__ == "__main__":
    unittest.main()
