"""Altair charts for comparing asset prices and normalized returns."""

import altair as alt
import pandas as pd

from btc_macro.transforms import to_chart_frame


def build_comparison_chart(
    prices: pd.DataFrame,
    is_normalized: bool,
    days_back: int,
) -> alt.LayerChart:
    """Build the interactive comparison chart from already transformed prices."""
    chart_df = to_chart_frame(prices)
    hover = alt.selection_point(fields=["Asset"], on="mouseover", clear="mouseout")

    y_domain = None
    if is_normalized:
        values = pd.to_numeric(chart_df["Value"], errors="coerce").dropna()
        if not values.empty:
            low, high = float(values.min()), float(values.max())
            pad = (high - low) * 0.15 if high != low else max(abs(high) * 0.15, 1.0)
            y_domain = [low - pad, high + pad]

    value_title = "% Change" if is_normalized else "Price (USD)"
    y_axis = alt.Y(
        "Value:Q",
        title=value_title,
        scale=(
            alt.Scale(domain=y_domain, zero=False, nice=True)
            if y_domain else alt.Scale(zero=False, nice=True)
        ),
        axis=alt.Axis(
            orient="right",
            labelColor="orange",
            titleColor="orange",
            labelAlign="center",
        ),
    )
    legend_order = (
        chart_df.dropna(subset=["Value"])
        .sort_values("Date")
        .groupby("Asset")["Value"]
        .last()
        .sort_values(ascending=False)
        .index.tolist()
    )
    main_chart = (
        alt.Chart(chart_df)
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(labelColor="orange", labelAlign="center")),
            y=y_axis,
            color=alt.Color(
                "Asset:N", sort=legend_order, legend=alt.Legend(title="Asset (sorted)")
            ),
            opacity=alt.condition(hover, alt.value(1.0), alt.value(0.25)),
            strokeWidth=alt.condition(hover, alt.value(3), alt.value(1.5)),
            tooltip=[
                alt.Tooltip("Date:T", title="Date"),
                alt.Tooltip("Asset:N", title="Ticker"),
                alt.Tooltip(
                    "Value:Q", title=value_title,
                    format=".2f" if is_normalized else ",.2f",
                ),
            ],
        )
        .add_params(hover)
    )

    # Use the first available observation in each month/year as its boundary.
    frequency = "M" if days_back <= 365 else "Y"
    boundaries = pd.DataFrame({"Date": chart_df["Date"]})
    boundaries["Boundary"] = boundaries["Date"].dt.to_period(frequency)
    boundaries = boundaries.drop_duplicates("Boundary")[["Date"]]
    rules = alt.Chart(boundaries).mark_rule(color="gray", strokeDash=[3, 3]).encode(x="Date:T")

    layers = [main_chart, rules]
    if is_normalized:
        baseline = (
            alt.Chart(pd.DataFrame({"y": [0]}))
            .mark_rule(strokeDash=[4, 4], color="orange")
            .encode(y="y:Q")
        )
        layers.append(baseline)

    return alt.layer(*layers).properties(width=800, height=600).interactive()
