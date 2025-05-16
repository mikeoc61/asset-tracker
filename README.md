# 📈 Asset Comparison Dashboard

[![Built with Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

A simple, interactive web dashboard to visualize and compare normalized asset returns (stocks, ETFs, crypto) over time.

## Features

- 📈 Download historical price data for selected tickers
- ⚡ Automatically patch in real-time crypto prices
- 📅 Date range selection with adjustment for non-trading days
- 🌎 Timezone-aware (local time zone detection)
- ✅ Ticker validity checking
- 📊 Normalize asset returns to compare performance over time
- 🧹 Clean, responsive Streamlit UI

## How to Run (locally)

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/your-repo-name.git
   cd your-repo-name

2. pip install -r requirements.txt
3. streamlit run asset_tracker.py
4. Open the local URL Streamlit gives you (usually http://localhost:8501).

## Requirements
	•	Python 3.9+
	•	Libraries listed in requirements.txt (e.g., streamlit, yfinance, pytz, tzlocal, pandas, altair, holidays)

## Notes
	•	Crypto tickers (e.g., BTC-USD) are updated with live prices if available.
	•	The app handles US market holidays and weekends automatically.
	•	Normalized % Change is the default view.
	•	Users can input a custom ticker directly during the session.

## License

MIT License. Feel free to use and modify!