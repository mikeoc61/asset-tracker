# 📈 Asset Comparison Dashboard

[![Tests](https://github.com/mikeoc61/asset-tracker/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/mikeoc61/asset-tracker/actions/workflows/tests.yml)
[![Built with Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

An interactive Streamlit dashboard for comparing the performance of stocks,
ETFs, mutual funds, market indexes, commodities, cryptocurrencies, and Treasury yields.

[Open the hosted dashboard](https://mikeoc61-asset-tracker.streamlit.app/)

## Features

- Download closing-price history from Yahoo Finance.
- Compare actual prices or normalized percentage returns.
- Toggle a matching-color, dashed 200-day SMA for every asset in closing-price mode.
- Select common assets or add a valid Yahoo Finance ticker.
- Asset picker names (such as Bitcoin and Dollar Index) are capped at 15 characters,
  including spaces. Edit `btc_macro/assets.py` to customize the name-to-ticker
  mapping. Custom assets fall back to their ticker; long labels use an ellipsis.
  Lookups and chart labels continue to use the full ticker symbol.
- Picker options sort alphabetically by displayed name on every redraw, including
  newly added custom tickers. Existing selections are preserved.
- Built-in choices include Fidelity Growth (FDGRX), Fidelity Bal. (FBAKX),
  Fidelity Semis (FSELX), and 10Y T-Note Yld (^TNX).
- Choose preset ranges from one week through five years, or custom start/end dates.
- Display mixed equity and cryptocurrency calendars on one chart.
- Patch the latest available crypto quotes into the current-day view.
- Highlight individual series and sort the closing-price legend by latest value.
- Read ticker and return labels at line endpoints in normalized mode.
- Cache historical downloads, ticker validation, and current quotes.

## Project structure

```text
asset_tracker.py          Streamlit entry point and chart UI
btc_macro/
  assets.py               Friendly asset names and compact picker labels
  charts.py               Interactive Altair chart construction
  dates.py                Calendar-date range calculations
  transforms.py           Price preparation and normalization
  yahoo.py                Yahoo Finance access and response handling
tests/
  test_app.py             Offline Streamlit date-range interaction tests
  test_dates.py           Preset and custom date-range tests
  test_charts.py          Chart structure and endpoint-label tests
  test_transforms.py      Data-transformation tests
  test_yahoo.py           Yahoo response and current-price tests
.github/workflows/
  tests.yml               GitHub Actions continuous integration
requirements.in           Direct production dependencies
requirements.txt          Pinned production dependency lock
```

## Local setup

Python 3.12 is recommended to match Streamlit Cloud and GitHub Actions.

```bash
git clone https://github.com/mikeoc61/asset-tracker.git
cd asset-tracker

python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Run the dashboard:

```bash
./venv/bin/python -m streamlit run asset_tracker.py \
  --server.address 127.0.0.1 \
  --server.port 8501
```

Then open [http://localhost:8501](http://localhost:8501).

The repository disables file watching by default. To reload local code edits
automatically, append `--server.fileWatcherType poll --server.runOnSave true`
to the command above. Otherwise, restart the server after editing imported modules.

## Testing

Run the unit tests:

```bash
./venv/bin/python -m unittest discover -v
```

The GitHub Actions workflow also runs the tests, compiles the Python source,
and verifies core imports on every push to `main` and on every pull request.
Workflow results are available under the repository's
[Actions tab](https://github.com/mikeoc61/asset-tracker/actions/workflows/tests.yml).

## Streamlit Cloud deployment

Streamlit Cloud deploys `asset_tracker.py` from the `main` branch. Most pushes
appear automatically after GitHub updates the repository.

If a deployment reports an import mismatch after files in `btc_macro/` change,
perform a full restart from **Manage app → ⋮ → Reboot app**. A full reboot makes
Streamlit Cloud clone the repository again and rebuild its Python environment;
clearing the application cache alone does not necessarily restart the process.

## Data notes

- `^TNX` represents the 10-year Treasury yield in percent, not a bond price.
  In closing-price mode, the chart identifies yield units when it is selected.
  Its normalized change is a relative change in yield, not a bond investment return.
- FSELX is Fidelity's Select Semiconductors portfolio, displayed as Fidelity Semis.
- The 200-day SMA uses 200 observed daily closes per asset (trading sessions for
  equities, calendar days for crypto), calculated before filling calendar gaps.
  Enable **Show 200-day SMA** in **Closing Price (USD)** mode; it is disabled in
  normalized mode. Hover highlights an asset's price and SMA together.
- SMA downloads include two extra years before the selected range. Assets with
  fewer than 200 closes in that history have no SMA until enough closes exist.
  Today's unfinished daily bar and current quotes are excluded; the latest
  completed average is carried forward to today and across market holidays.
- Normalized percentage change is the default chart view.
- Each asset is normalized from its first valid value in the selected range.
- Crypto trades continuously, while other assets follow their market calendars.
- Requested ranges preserve weekend and holiday starts; each asset begins at its
  first available observation. YTD starts on January 1.
- For custom ranges, select **Custom** under **Time Range**, choose the start and
  end dates, and click **Apply dates**. Both dates are included; future dates and
  reversed ranges are not allowed. A single-day range displays points. Applied
  custom dates are remembered while switching presets within the same session.
- Historical ranges ending before today use closing-price history only; current
  crypto quotes are added only when the selected range ends today.
- Dates use the runtime machine's timezone (shown beneath the chart), which may
  differ between local and hosted deployments.
- Current crypto-price lookup failures are non-fatal; historical data still renders.
- Market data is provided for informational and visualization purposes.

## License

MIT License.
