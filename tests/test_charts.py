import unittest

import pandas as pd

from btc_macro.charts import build_comparison_chart


class ComparisonChartTests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.DataFrame(
            {"SPY": [0.0, 10.0, None], "BTC-USD": [0.0, 20.0, 30.0]},
            index=pd.to_datetime(["2025-01-02", "2025-02-03", "2026-01-02"]),
        )

    def test_normalized_chart_preserves_baseline_legend_and_padded_domain(self):
        spec = build_comparison_chart(self.prices, True, 365).to_dict()
        self.assertEqual(len(spec["layer"]), 3)
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


if __name__ == "__main__":
    unittest.main()
