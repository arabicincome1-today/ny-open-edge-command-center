#!/usr/bin/env python3
"""
Download real market candles to CSV.

Default target is NQ futures from Yahoo Finance:
    python3 download_candles.py

Then run:
    python3 ny_open_edge_dashboard.py NQ_1m.csv --point-value 20
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Download real OHLCV candles for the edge dashboard.")
    parser.add_argument("--symbol", default="NQ=F", help="Yahoo Finance symbol. Examples: NQ=F, MNQ=F, ES=F, SPY.")
    parser.add_argument("--interval", default="1m", help="Candle interval. Examples: 1m, 2m, 5m, 15m, 1h, 1d.")
    parser.add_argument("--period", default="5d", help="Lookback period. Examples: 1d, 5d, 1mo, 3mo.")
    parser.add_argument("--out", type=Path, default=Path("NQ_1m.csv"), help="Output CSV file.")
    args = parser.parse_args()

    try:
        import yfinance as yf
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: yfinance\n\n"
            "Install it with:\n"
            "    python3 -m pip install -r requirements.txt\n"
        ) from exc

    data = yf.download(
        args.symbol,
        period=args.period,
        interval=args.interval,
        auto_adjust=False,
        progress=False,
        prepost=True,
    )

    if data.empty:
        raise SystemExit(f"No candles returned for {args.symbol}. Try a different symbol, period, or interval.")

    data = data.reset_index()
    timestamp_col = "Datetime" if "Datetime" in data.columns else "Date"

    # yfinance may return multi-level columns for some versions/symbols.
    if hasattr(data.columns, "get_level_values") and len(data.columns.names) > 1:
        data.columns = [str(col[0]).lower() if isinstance(col, tuple) else str(col).lower() for col in data.columns]
        timestamp_col = "datetime" if "datetime" in data.columns else "date"
    else:
        data.columns = [str(col).lower() for col in data.columns]
        timestamp_col = timestamp_col.lower()

    rename_map = {
        timestamp_col: "timestamp",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
    }
    data = data.rename(columns=rename_map)

    required = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise SystemExit(f"Downloaded data is missing columns: {', '.join(missing)}")

    data = data[required].dropna(subset=["open", "high", "low", "close"])
    data.to_csv(args.out, index=False)

    print(f"Saved {len(data)} candles for {args.symbol} to {args.out}")
    print("Next run:")
    print(f"    python3 ny_open_edge_dashboard.py {args.out} --point-value 20")


if __name__ == "__main__":
    main()
