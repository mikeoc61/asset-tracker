import unittest
from datetime import date

import pandas as pd
from pandas.testing import assert_frame_equal

from btc_macro.yahoo import (
    apply_current_prices,
    download_close_prices,
    extract_close_prices,
    fetch_current_prices,
    ticker_has_recent_data,
)


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


class YahooAccessTests(unittest.TestCase):
    def test_download_close_prices_normalizes_download(self):
        columns = pd.MultiIndex.from_tuples(
            [("Close", "SPY")],
            names=["Price", "Ticker"],
        )
        response = pd.DataFrame(
            [[100.0]],
            columns=columns,
            index=pd.to_datetime(["2025-01-02"]),
        )
        calls = []

        def downloader(tickers, **kwargs):
            calls.append((tickers, kwargs))
            return response

        result = download_close_prices(["SPY"], "2025-01-01", downloader)

        self.assertEqual(result.columns.tolist(), ["SPY"])
        self.assertEqual(
            calls,
            [(["SPY"], {"start": "2025-01-01", "progress": False})],
        )

    def test_empty_download_has_a_clear_error(self):
        def downloader(*args, **kwargs):
            return pd.DataFrame()

        with self.assertRaisesRegex(RuntimeError, "returned no data"):
            download_close_prices(["SPY"], "2025-01-01", downloader)

    def test_ticker_validation_handles_success_and_failure(self):
        valid = lambda *args, **kwargs: pd.DataFrame({"Close": [100.0]})

        def failing(*args, **kwargs):
            raise ConnectionError("offline")

        self.assertTrue(ticker_has_recent_data("SPY", valid))
        self.assertFalse(ticker_has_recent_data("SPY", failing))

    def test_current_price_lookup_omits_failures(self):
        class Quote:
            def __init__(self, price):
                self.info = {"regularMarketPrice": price}

        def factory(ticker):
            if ticker == "ETH-USD":
                raise ConnectionError("offline")
            return Quote(123.45)

        result = fetch_current_prices(["BTC-USD", "ETH-USD"], factory)

        self.assertEqual(result, {"BTC-USD": 123.45})


class ApplyCurrentPricesTests(unittest.TestCase):
    def test_appends_one_shared_row_for_multiple_current_prices(self):
        prices = pd.DataFrame(
            {
                "SPY": [100.0],
                "BTC-USD": [200.0],
                "ETH-USD": [300.0],
            },
            index=pd.to_datetime(["2025-01-01"]),
        )
        original = prices.copy()

        result = apply_current_prices(
            prices,
            {"BTC-USD": 210.0, "ETH-USD": 320.0},
            date(2025, 1, 2),
        )

        self.assertEqual(
            result.index.tolist(),
            pd.to_datetime(["2025-01-01", "2025-01-02"]).tolist(),
        )
        self.assertTrue(pd.isna(result.at[pd.Timestamp("2025-01-02"), "SPY"]))
        self.assertEqual(result.at[pd.Timestamp("2025-01-02"), "BTC-USD"], 210.0)
        self.assertEqual(result.at[pd.Timestamp("2025-01-02"), "ETH-USD"], 320.0)
        assert_frame_equal(prices, original)

    def test_updates_existing_as_of_row_without_adding_a_duplicate(self):
        prices = pd.DataFrame(
            {"BTC-USD": [200.0, 205.0]},
            index=pd.to_datetime(["2025-01-01", "2025-01-02"]),
        )

        result = apply_current_prices(
            prices,
            {"BTC-USD": 210.0},
            date(2025, 1, 2),
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[-1]["BTC-USD"], 210.0)

    def test_ignores_unknown_tickers_and_missing_quotes(self):
        prices = pd.DataFrame(
            {"BTC-USD": [200.0]},
            index=pd.to_datetime(["2025-01-01"]),
        )

        result = apply_current_prices(
            prices,
            {"UNKNOWN": 10.0, "BTC-USD": float("nan")},
            date(2025, 1, 2),
        )

        assert_frame_equal(result, prices)


if __name__ == "__main__":
    unittest.main()
