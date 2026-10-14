"""Friendly picker labels keyed by the symbols used for market-data lookups."""

ASSET_NAMES = {
    "SPY": "S&P 500",
    "EFA": "EAFE Markets",
    "IWM": "Russell 2000",
    "QQQ": "Nasdaq 100",
    "FDGRX": "Fidelity Growth",
    "FBAKX": "Fidelity Bal.",
    "FSELX": "Fidelity Semis",
    "STRK": "STRK Preferred",
    "NVDA": "Nvidia",
    "AAPL": "Apple",
    "TSLA": "Tesla",
    "^DJI": "Dow Jones",
    "^TNX": "10Y T-Note Yld",
    "DX-Y.NYB": "Dollar Index",
    "GC=F": "Gold Futures",
    "SI=F": "Silver Futures",
    "HG=F": "Copper Futures",
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "SOL-USD": "Solana",
}

MAX_ASSET_LABEL_LENGTH = 15


def asset_label(ticker: str) -> str:
    """Format a picker label, falling back to the symbol for custom assets."""
    name = ASSET_NAMES.get(ticker, ticker)
    if len(name) > MAX_ASSET_LABEL_LENGTH:
        return name[:MAX_ASSET_LABEL_LENGTH - 1] + "…"
    return name
