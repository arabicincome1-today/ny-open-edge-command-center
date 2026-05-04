NY Open Edge Command Center
A clean Python dashboard for monitoring New York Open trading edges from OHLCV candle data.

The goal is simple: keep all your setups in one place, calculate the same risk model every time, and leave room to add more edges and machine learning filters later.

Current Edges
Edge	Logic
Opening Range Break	Builds the 9:30-9:45 NY opening range. Close above = long. Close below = short.
9:30 Sweep Reversal	Sweeping the 9:30 high suggests short reversal. Sweeping the 9:30 low suggests long reversal.
Risk Model
Default settings:

Setting	Value
Risk per setup	$1,000
Stop loss	50 points
Target	2R
The script calculates quantity using:

quantity = risk dollars / (stop points * point value)
For example, NQ futures use a point value of 20:

python3 ny_open_edge_dashboard.py sample_candles.csv --point-value 20
Quick Start
Run with the sample data:

python3 ny_open_edge_dashboard.py sample_candles.csv
Run with your own candles:

python3 ny_open_edge_dashboard.py your_candles.csv --point-value 20
Generated files:

ny_open_edge_triggers.csv
ny_open_edge_alerts.txt
CSV Format
Your input file should use these columns:

timestamp,open,high,low,close,volume
2026-05-01 09:30:00,100,105,98,102,12345
If timestamps do not include a timezone, the script assumes they are already New York time.

Adding More Edges
Each edge is a detector function. Add a new function like this:

def detect_my_next_edge(context: EdgeContext) -> EdgeTrigger | None:
    candle = context.candle
    state = context.state
    risk = context.risk

    # Your setup logic here.
    return None
Then register it:

def get_edge_detectors() -> list[EdgeDetector]:
    return [
        detect_opening_range_break,
        detect_930_sweep_reversal,
        detect_my_next_edge,
    ]
ML Roadmap
The project is structured so machine learning can be added later:

Log setup features.
Label whether each setup hit target or stop first.
Train a model to score setup quality.
Use the model as a filter before alerts.
The first model should be a filter, not a replacement for the trading edge.
