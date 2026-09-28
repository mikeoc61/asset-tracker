# 📈 Asset Comparison Dashboard

[![Tests](https://github.com/mikeoc61/asset-tracker/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/mikeoc61/asset-tracker/actions/workflows/tests.yml)
[![Built with Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

An interactive Streamlit dashboard for comparing the performance of stocks,
ETFs, market indexes, commodities, and cryptocurrencies.

[Open the hosted dashboard](https://mikeoc61-asset-tracker.streamlit.app/)

## Features

- Download closing-price history from Yahoo Finance.
- Compare actual prices or normalized percentage returns.
- Select common assets or add a valid Yahoo Finance ticker.
- Choose ranges from one week through five years.
- Display mixed equity and cryptocurrency calendars on one chart.
- Patch the latest available crypto quotes into the current-day view.
- Highlight individual series and sort the legend by latest value.
- Cache historical downloads, ticker validation, and current quotes.

## Project structure

```text
asset_tracker.py          Streamlit entry point and chart UI
btc_macro/
  charts.py               Interactive Altair chart construction
  dates.py                Calendar-date range calculations
  transforms.py           Price preparation and normalization
  yahoo.py                Yahoo Finance access and response handling
tests/
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

- Normalized percentage change is the default chart view.
- Each asset is normalized from its first valid value in the selected range.
- Crypto trades continuously, while other assets follow their market calendars.
- Requested ranges preserve weekend and holiday starts; each asset begins at its
  first available observation. YTD starts on January 1.
- Dates use the runtime machine's timezone (shown beneath the chart), which may
  differ between local and hosted deployments.
- Current crypto-price lookup failures are non-fatal; historical data still renders.
- Market data is provided for informational and visualization purposes.

## License

MIT License.
