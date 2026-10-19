"""Exercise date-range interactions without contacting Yahoo Finance."""

import io
import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pyarrow.ipc as ipc
import streamlit as st
import tzlocal
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "asset_tracker.py"


class CustomDateRangeAppTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()
        self.addCleanup(st.cache_data.clear)
        self.today = datetime.now(tzlocal.get_localzone()).date()
        self.start = self.today - timedelta(days=60)
        self.end = self.today - timedelta(days=30)
        download_patch = patch("btc_macro.yahoo.download_close_prices", side_effect=self._history)
        quotes_patch = patch("btc_macro.yahoo.fetch_current_prices", return_value={"BTC-USD": 999.0})
        self.download = download_patch.start()
        self.quotes = quotes_patch.start()
        self.addCleanup(download_patch.stop)
        self.addCleanup(quotes_patch.stop)
        self.app = AppTest.from_file(str(APP_PATH)).run(timeout=15)
        self._assert_no_errors()

    @staticmethod
    def _history(tickers, starting_date, *, ending_date):
        start, end = pd.Timestamp(starting_date), pd.Timestamp(ending_date)
        dates = sorted({start - pd.Timedelta(days=1), start, end, end + pd.Timedelta(days=1)})
        # Include out-of-range rows to also verify the dashboard's final filter.
        return pd.DataFrame(
            {
                ticker: [
                    (80.0 if day < start else 100.0 if day == start else 120.0 if day == end else 900.0)
                    for day in dates
                ]
                for ticker in tickers
            },
            index=dates,
        )

    def _assert_no_errors(self):
        self.assertEqual(list(self.app.exception), [])
        self.assertEqual(list(self.app.error), [])

    def _choose_custom(self, start, end, assets=None):
        self.app.selectbox[0].select("Custom").run()
        self.app.date_input(key="custom_start").set_value(start)
        self.app.date_input(key="custom_end").set_value(end)
        if assets is not None:
            self.app.multiselect[0].set_value(assets)
        self.app.button[0].click().run()

    def _chart_data(self):
        proto = self.app.get("arrow_vega_lite_chart")[0].proto
        spec = json.loads(proto.spec)
        name = spec["layer"][0]["data"]["name"]
        dataset = next(dataset for dataset in proto.datasets if dataset.name == name)
        return spec, ipc.open_stream(io.BytesIO(dataset.data.data)).read_all().to_pandas()

    def test_historical_range_is_inclusive_in_both_modes_and_skips_current_quotes(self):
        self._choose_custom(self.start, self.end, ["SPY", "BTC-USD"])
        self._assert_no_errors()
        self.download.assert_called_with(
            ["BTC-USD", "SPY"], self.start.isoformat(), ending_date=self.end.isoformat(),
        )
        self.quotes.assert_not_called()
        _, data = self._chart_data()
        self.assertEqual(
            set(pd.to_datetime(data["Date"]).dt.date), {self.start, self.end},
        )
        for _, series in data.groupby("Asset"):
            self.assertAlmostEqual(series["Value"].iloc[0], 0.0)
            self.assertAlmostEqual(series["Value"].iloc[-1], 20.0)
        self.assertIn(
            f"**Requested date range:** {self.start.isoformat()} to {self.end.isoformat()}",
            [caption.value for caption in self.app.caption],
        )

        self.app.radio[0].set_value("Closing Price (USD)").run()
        self._assert_no_errors()
        _, data = self._chart_data()
        self.assertEqual(set(data["Value"]), {100.0, 120.0})
        self.quotes.assert_not_called()

    def test_custom_ticker_uses_readable_name_and_retains_lookup_symbol(self):
        with patch("btc_macro.yahoo.ticker_has_recent_data", return_value=True), patch(
            "btc_macro.yahoo.fetch_asset_name", return_value="Microsoft Corporation",
        ) as names:
            self.app.run()
            self.app.text_input(key="user_input").set_value("msft").run()
            self._assert_no_errors()
            picker = self.app.multiselect[0]
            self.assertIn("Microsoft Corporati…", picker.options)
            self.assertIn("MSFT", picker.value)
            self.assertIn("MSFT", self.download.call_args.args[0])
            self.assertEqual(picker.options, sorted(picker.options, key=str.casefold))
            self.app.run()
            self._assert_no_errors()
            names.assert_called_once_with("MSFT")

    def test_changing_end_date_uses_a_separate_cache_entry(self):
        self._choose_custom(self.start, self.end)
        calls = self.download.call_count
        new_end = self.end + timedelta(days=1)
        self.app.date_input(key="custom_end").set_value(new_end)
        self.app.button[0].click().run()
        self._assert_no_errors()
        self.assertEqual(self.download.call_count, calls + 1)
        self.assertEqual(self.download.call_args.kwargs["ending_date"], new_end.isoformat())

        self.app.button[0].click().run()
        self.assertEqual(self.download.call_count, calls + 1)

    def test_sma_toggle_history_modes_and_live_quote_exclusion(self):
        def history(tickers, starting_date, *, ending_date):
            dates = pd.date_range(starting_date, ending_date)
            return pd.DataFrame({ticker: 100.0 for ticker in tickers}, index=dates)

        self.download.side_effect = history
        st.cache_data.clear()
        self._choose_custom(self.today - timedelta(days=7), self.today, ["SPY", "BTC-USD"])
        self.assertTrue(self.app.toggle[0].disabled)
        self.assertFalse(self.app.toggle[0].value)
        self.app.radio[0].set_value("Closing Price (USD)").run()
        _, original = self._chart_data()
        self.app.toggle[0].set_value(True).run()
        self._assert_no_errors()
        self.assertEqual(
            self.download.call_args.args[1],
            (self.today - timedelta(days=737)).isoformat(),
        )
        spec, prices = self._chart_data()
        pd.testing.assert_frame_equal(prices, original)
        self.assertEqual(len(spec["layer"]), 3)
        proto = self.app.get("arrow_vega_lite_chart")[0].proto
        name = spec["layer"][2]["data"]["name"]
        dataset = next(item for item in proto.datasets if item.name == name)
        sma = ipc.open_stream(io.BytesIO(dataset.data.data)).read_all().to_pandas()
        self.assertEqual(set(sma["Value"]), {100.0})
        self.assertEqual(set(sma["Asset"]), {"SPY", "BTC-USD"})
        self.assertEqual(pd.to_datetime(sma["Date"]).min().date(), self.today - timedelta(days=7))

        self.app.radio[0].set_value("Normalized % Change").run()
        self._assert_no_errors()
        self.assertTrue(self.app.toggle[0].disabled)
        spec, _ = self._chart_data()
        self.assertFalse(any(layer["mark"].get("strokeDash") == [6, 4] for layer in spec["layer"]))
        self.app.radio[0].set_value("Closing Price (USD)").run()
        self.assertTrue(self.app.toggle[0].value)
        self.app.toggle[0].set_value(False).run()
        self._assert_no_errors()
        spec, _ = self._chart_data()
        self.assertEqual(len(spec["layer"]), 2)

    def test_reversed_range_stops_before_download_and_can_be_corrected(self):
        self.app.selectbox[0].select("Custom").run()
        calls = self.download.call_count
        self.app.date_input(key="custom_start").set_value(self.end)
        self.app.date_input(key="custom_end").set_value(self.start)
        self.app.button[0].click().run()
        self._assert_no_errors()
        self.assertEqual(self.download.call_count, calls)
        self.assertIn("on or before", self.app.warning[0].value)
        self.assertEqual(self.app.get("arrow_vega_lite_chart"), [])

        self.app.date_input(key="custom_start").set_value(self.start)
        self.app.date_input(key="custom_end").set_value(self.end)
        self.app.button[0].click().run()
        self._assert_no_errors()
        self.assertEqual(len(self.app.get("arrow_vega_lite_chart")), 1)

    def test_range_ending_today_keeps_current_crypto_quotes(self):
        self._choose_custom(self.start, self.today, ["SPY", "BTC-USD"])
        self._assert_no_errors()
        self.quotes.assert_called_once_with(["BTC-USD"])
        _, data = self._chart_data()
        crypto = data[data["Asset"] == "BTC-USD"]
        self.assertAlmostEqual(crypto["Value"].iloc[-1], 899.0)
        self.assertEqual(pd.to_datetime(crypto["Date"]).iloc[-1].date(), self.today)

    def test_switching_back_to_a_preset_restores_today_end(self):
        self._choose_custom(self.start, self.end)
        self.app.selectbox[0].select("YTD").run()
        self._assert_no_errors()
        self.assertEqual(list(self.app.date_input), [])
        self.assertEqual(self.download.call_args.args[1], f"{self.today.year}-01-01")
        self.assertEqual(self.download.call_args.kwargs["ending_date"], self.today.isoformat())

        self.app.selectbox[0].select("Custom").run()
        self._assert_no_errors()
        self.assertEqual(self.app.date_input(key="custom_start").value, self.start)
        self.assertEqual(self.app.date_input(key="custom_end").value, self.end)

    def test_mtd_picker_requests_current_month_through_today(self):
        self.app.selectbox[0].select("MTD").run()
        self._assert_no_errors()
        self.assertEqual(
            self.download.call_args.args[1], self.today.replace(day=1).isoformat(),
        )
        self.assertEqual(self.download.call_args.kwargs["ending_date"], self.today.isoformat())

    def test_no_data_error_does_not_add_quotes_or_render_a_chart(self):
        self.app.selectbox[0].select("Custom").run()
        self.download.side_effect = RuntimeError("Yahoo Finance returned no data for the selected range.")
        self.app.date_input(key="custom_start").set_value(self.start)
        self.app.date_input(key="custom_end").set_value(self.end)
        self.app.multiselect[0].set_value(["SPY", "BTC-USD"])
        self.app.button[0].click().run()

        self.assertEqual(list(self.app.exception), [])
        self.assertIn("returned no data", self.app.error[0].value)
        self.assertEqual(self.app.get("arrow_vega_lite_chart"), [])
        self.quotes.assert_not_called()


if __name__ == "__main__":
    unittest.main()
