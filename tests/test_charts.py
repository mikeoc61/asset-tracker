import unittest

import pandas as pd

from btc_macro.charts import _endpoint_labels, build_comparison_chart
from btc_macro.transforms import to_chart_frame


class ComparisonChartTests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.DataFrame(
            {"SPY": [0.0, 10.0, None], "BTC-USD": [0.0, 20.0, 30.0]},
            index=pd.to_datetime(["2025-01-02", "2025-02-03", "2026-01-02"]),
        )

    def test_normalized_chart_preserves_baseline_legend_and_padded_domain(self):
        spec = build_comparison_chart(self.prices, True, 365).to_dict()
        self.assertEqual(len(spec["layer"]), 5)
        encoding = spec["layer"][0]["encoding"]
        self.assertEqual(encoding["color"]["sort"], ["BTC-USD", "SPY"])
        self.assertEqual(encoding["y"]["title"], "% Change")
        self.assertEqual(encoding["y"]["scale"]["domain"], [-4.5, 34.5])
        self.assertTrue(any(p.get("select", {}).get("on") == "mouseover" for p in spec["params"]))

    def test_price_chart_omits_zero_baseline_and_groups_boundaries_by_year(self):
        spec = build_comparison_chart(self.prices, False, 1095).to_dict()
        self.assertEqual(len(spec["layer"]), 2)
        self.assertEqual(spec["layer"][0]["encoding"]["y"]["title"], "Price (USD)")
        boundary_data = spec["datasets"][spec["layer"][1]["data"]["name"]]
        self.assertEqual(len(boundary_data), 2)

    def test_constant_normalized_data_has_nonzero_y_range(self):
        prices = pd.DataFrame({"SPY": [0.0]}, index=pd.to_datetime(["2026-01-02"]))
        spec = build_comparison_chart(prices, True, 7).to_dict()
        self.assertEqual(spec["layer"][0]["encoding"]["y"]["scale"]["domain"], [-1.0, 1.0])

    def test_labels_use_each_assets_last_valid_return_and_date(self):
        spec = build_comparison_chart(self.prices, True, 365).to_dict()
        text_layer = spec["layer"][-1]
        rows = spec["datasets"][text_layer["data"]["name"]]
        labels = {row["Asset"]: row for row in rows}
        self.assertEqual(labels["SPY"]["Label"], "SPY +10.0%")
        self.assertTrue(labels["SPY"]["Date"].startswith("2025-02-03"))
        self.assertEqual(labels["BTC-USD"]["Label"], "BTC-USD +30.0%")
        self.assertEqual(labels["BTC-USD"]["Value"], 30.0)

    def test_close_returns_get_separated_without_changing_actual_values(self):
        prices = pd.DataFrame(
            {"A": [9.99], "B": [10.0], "C": [10.01], "LOSS": [-2.5]},
            index=pd.to_datetime(["2026-01-02"]),
        )
        labels = _endpoint_labels(to_chart_frame(prices), [-5.0, 15.0])
        self.assertGreaterEqual(labels["LabelValue"].diff().dropna().min(), 0.6 - 1e-10)
        self.assertTrue(labels["LabelValue"].between(-4.6, 14.6).all())
        self.assertEqual(labels.set_index("Asset").at["LOSS", "Label"], "LOSS -2.5%")
        self.assertEqual(labels.set_index("Asset").at["C", "Value"], 10.01)


if __name__ == "__main__":
    unittest.main()
