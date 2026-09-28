"""Altair charts for comparing asset prices and normalized returns."""

import altair as alt
import pandas as pd

from btc_macro.transforms import to_chart_frame


def _endpoint_labels(chart_df: pd.DataFrame, y_domain: list[float]) -> pd.DataFrame:
    """Keep endpoint labels ordered and spaced within the chart's y domain."""
    endpoints = (
        chart_df.dropna(subset=["Value"])
        .sort_values("Date")
        .groupby("Asset", sort=False)
        .tail(1)
        .sort_values(["Value", "Asset"])
        .copy()
    )
    if endpoints.empty:
        return endpoints

    low, high = y_domain
    span = high - low
    lower, upper = low + span * 0.02, high - span * 0.02
    # Eighteen pixels between labels at the default 600-pixel chart height.
    gap = min(span * 18 / 600, (upper - lower) / max(len(endpoints) - 1, 1))
    positions = []
    for value in endpoints["Value"]:
        positions.append(max(float(value), lower, positions[-1] + gap if positions else lower))
    positions[-1] = min(positions[-1], upper)
    for index in range(len(positions) - 2, -1, -1):
        positions[index] = min(positions[index], positions[index + 1] - gap)

    endpoints["LabelValue"] = positions
    endpoints["Label"] = [
        f"{asset} {0.0 if abs(value) < 0.05 else value:+.1f}%"
        for asset, value in zip(endpoints["Asset"], endpoints["Value"])
    ]
    return endpoints


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
    x_scale = alt.Scale()
    labels = pd.DataFrame()
    if is_normalized and y_domain:
        labels = _endpoint_labels(chart_df, y_domain)
        first_date, last_date = chart_df["Date"].min(), chart_df["Date"].max()
        if first_date == last_date:
            first_date -= pd.Timedelta(days=1)
        date_span = max(last_date - first_date, pd.Timedelta(days=1))
        # Reserve pixels for text, rather than a fraction of the date range.
        # Vega's width signal keeps this allowance compact as Streamlit resizes.
        text_width = min(float(labels["Label"].str.len().max()) * 6.5, 140)
        reserved_pixels = text_width + 28
        last_ms = f"toNumber(toDate('{last_date.isoformat()}'))"
        span_ms = date_span.total_seconds() * 1000
        denominator = f"max(width - {reserved_pixels}, 1)"
        label_date_expression = f"{last_ms} + {span_ms} * 12 / {denominator}"
        x_scale = alt.Scale(
            domainMin=alt.ExprRef(expr=f"toDate('{first_date.isoformat()}')"),
            domainMax=alt.ExprRef(
                expr=f"{last_ms} + {span_ms} * {reserved_pixels} / {denominator}"
            ),
        )

    color = alt.Color(
        "Asset:N", sort=legend_order,
        legend=None if is_normalized else alt.Legend(title="Asset (sorted)"),
    )
    main_chart = (
        alt.Chart(chart_df)
        .mark_line(point=prices.index.nunique() == 1)
        .encode(
            x=alt.X(
                "Date:T", title="Date", scale=x_scale,
                axis=alt.Axis(labelColor="orange", labelAlign="center"),
            ),
            y=y_axis,
            color=color,
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
        if not labels.empty:
            connectors = (
                alt.Chart(labels)
                .transform_calculate(LabelDate=label_date_expression)
                .mark_rule(strokeWidth=1, opacity=0.5)
                .encode(
                    x=alt.X("Date:T", title="Date"), x2="LabelDate:T",
                    y=alt.Y("Value:Q", title=value_title), y2="LabelValue:Q",
                    color=color,
                )
            )
            endpoint_text = (
                alt.Chart(labels)
                .transform_calculate(LabelDate=label_date_expression)
                .mark_text(align="left", baseline="middle", dx=6, fontSize=11, limit=140)
                .encode(
                    x=alt.X("LabelDate:T", title="Date"),
                    y=alt.Y("LabelValue:Q", title=value_title), text="Label:N",
                    color=color,
                    opacity=alt.condition(hover, alt.value(1.0), alt.value(0.4)),
                    tooltip=[
                        alt.Tooltip("Asset:N", title="Ticker"),
                        alt.Tooltip("Date:T", title="Latest observation"),
                        alt.Tooltip("Value:Q", title="% Change", format="+.2f"),
                    ],
                )
            )
            layers.extend([connectors, endpoint_text])

    return alt.layer(*layers).properties(width=800, height=600).interactive()
