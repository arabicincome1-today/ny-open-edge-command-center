#!/usr/bin/env python3
"""
NY Open Edge Command Center

Reads OHLCV candles from a CSV file and monitors multiple New York Open edges
in one place.

Expected CSV columns:
    timestamp,open,high,low,close,volume

Timestamp examples:
    2026-05-01 09:30:00
    2026-05-01T09:30:00-04:00

If timestamps are timezone-naive, they are assumed to already be New York time.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Callable, Iterable
from zoneinfo import ZoneInfo


NY_TZ = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @property
    def ny_time(self) -> datetime:
        if self.timestamp.tzinfo is None:
            return self.timestamp.replace(tzinfo=NY_TZ)
        return self.timestamp.astimezone(NY_TZ)

    @property
    def ny_date(self):
        return self.ny_time.date()


@dataclass(frozen=True)
class EdgeTrigger:
    edge: str
    direction: str
    timestamp: datetime
    entry: float
    stop: float
    target: float
    qty: float
    risk_dollars: float
    stop_points: float
    target_r: float
    alert_message: str


@dataclass
class DayState:
    opening_range_high: float | None = None
    opening_range_low: float | None = None
    candle_930_high: float | None = None
    candle_930_low: float | None = None
    orb_triggered: bool = False
    sweep_triggered: bool = False
    custom: dict[str, bool] | None = None


@dataclass(frozen=True)
class RiskConfig:
    risk_dollars: float = 1000.0
    stop_points: float = 50.0
    target_r: float = 2.0
    point_value: float = 1.0
    require_close_back_inside: bool = True


@dataclass(frozen=True)
class EdgeContext:
    candle: Candle
    state: DayState
    risk: RiskConfig


EdgeDetector = Callable[[EdgeContext], EdgeTrigger | None]


def parse_timestamp(value: str) -> datetime:
    value = value.strip()
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unsupported timestamp format: {value!r}")


def read_candles(path: Path) -> list[Candle]:
    candles: list[Candle] = []
    with path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        required = {"timestamp", "open", "high", "low", "close"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

        for row in reader:
            candles.append(
                Candle(
                    timestamp=parse_timestamp(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0),
                )
            )

    return sorted(candles, key=lambda candle: candle.ny_time)


def in_window(candle: Candle, start: time, end: time) -> bool:
    t = candle.ny_time.time()
    return start <= t < end


def is_930_candle(candle: Candle) -> bool:
    t = candle.ny_time.time()
    return t.hour == 9 and t.minute == 30


def build_trigger(
    edge: str,
    direction: str,
    candle: Candle,
    risk_dollars: float,
    stop_points: float,
    target_r: float,
    point_value: float,
) -> EdgeTrigger:
    entry = candle.close
    if direction == "long":
        stop = entry - stop_points
        target = entry + stop_points * target_r
    else:
        stop = entry + stop_points
        target = entry - stop_points * target_r

    qty = risk_dollars / (stop_points * point_value)
    alert_message = (
        f"{edge} {direction.upper()} | "
        f"Entry {entry:.2f} | SL {stop:.2f} | TP {target:.2f} | "
        f"Risk ${risk_dollars:.0f} | Qty {qty:.2f}"
    )

    return EdgeTrigger(
        edge=edge,
        direction=direction,
        timestamp=candle.ny_time,
        entry=entry,
        stop=stop,
        target=target,
        qty=qty,
        risk_dollars=risk_dollars,
        stop_points=stop_points,
        target_r=target_r,
        alert_message=alert_message,
    )


def detect_opening_range_break(context: EdgeContext) -> EdgeTrigger | None:
    candle = context.candle
    state = context.state
    risk = context.risk
    orb_trade_window = (time(9, 45), time(12, 0))

    if (
        in_window(candle, *orb_trade_window)
        and not state.orb_triggered
        and state.opening_range_high is not None
        and state.opening_range_low is not None
    ):
        if candle.close > state.opening_range_high:
            state.orb_triggered = True
            return build_trigger(
                "Opening Range Break",
                "long",
                candle,
                risk.risk_dollars,
                risk.stop_points,
                risk.target_r,
                risk.point_value,
            )

        if candle.close < state.opening_range_low:
            state.orb_triggered = True
            return build_trigger(
                "Opening Range Break",
                "short",
                candle,
                risk.risk_dollars,
                risk.stop_points,
                risk.target_r,
                risk.point_value,
            )

    return None


def detect_930_sweep_reversal(context: EdgeContext) -> EdgeTrigger | None:
    candle = context.candle
    state = context.state
    risk = context.risk
    sweep_trade_window = (time(9, 31), time(12, 0))

    if (
        in_window(candle, *sweep_trade_window)
        and not state.sweep_triggered
        and state.candle_930_high is not None
        and state.candle_930_low is not None
    ):
        high_swept = candle.high > state.candle_930_high
        low_swept = candle.low < state.candle_930_low
        short_confirmed = high_swept and (not risk.require_close_back_inside or candle.close < state.candle_930_high)
        long_confirmed = low_swept and (not risk.require_close_back_inside or candle.close > state.candle_930_low)

        if short_confirmed:
            state.sweep_triggered = True
            return build_trigger(
                "9:30 Sweep Reversal",
                "short",
                candle,
                risk.risk_dollars,
                risk.stop_points,
                risk.target_r,
                risk.point_value,
            )

        if long_confirmed:
            state.sweep_triggered = True
            return build_trigger(
                "9:30 Sweep Reversal",
                "long",
                candle,
                risk.risk_dollars,
                risk.stop_points,
                risk.target_r,
                risk.point_value,
            )

    return None


def get_edge_detectors() -> list[EdgeDetector]:
    """Add future setup detectors here."""
    return [
        detect_opening_range_break,
        detect_930_sweep_reversal,
        # Future edge:
        # detect_my_next_edge,
    ]


def update_shared_day_state(candle: Candle, state: DayState) -> None:
    opening_range = (time(9, 30), time(9, 45))

    if in_window(candle, *opening_range):
        state.opening_range_high = (
            candle.high if state.opening_range_high is None else max(state.opening_range_high, candle.high)
        )
        state.opening_range_low = candle.low if state.opening_range_low is None else min(state.opening_range_low, candle.low)

    if is_930_candle(candle) and state.candle_930_high is None:
        state.candle_930_high = candle.high
        state.candle_930_low = candle.low


def detect_edges(candles: Iterable[Candle], risk: RiskConfig) -> list[EdgeTrigger]:
    states: dict[object, DayState] = {}
    triggers: list[EdgeTrigger] = []
    detectors = get_edge_detectors()

    for candle in candles:
        state = states.setdefault(candle.ny_date, DayState(custom={}))
        update_shared_day_state(candle, state)

        context = EdgeContext(candle=candle, state=state, risk=risk)
        for detector in detectors:
            trigger = detector(context)
            if trigger is not None:
                triggers.append(trigger)

    return triggers


def print_dashboard(triggers: list[EdgeTrigger]) -> None:
    by_edge: dict[str, list[EdgeTrigger]] = {}
    for trigger in triggers:
        by_edge.setdefault(trigger.edge, []).append(trigger)

    print("\n" + "=" * 104)
    print(" NY OPEN EDGE COMMAND CENTER ".center(104, "="))
    print("=" * 104)
    print(f"{'EDGE':<30} {'SIGNALS':>8} {'LAST SIDE':>12} {'LAST TIME':>24} {'ENTRY':>12} {'STATUS':>10}")
    print("-" * 104)

    for edge in ("Opening Range Break", "9:30 Sweep Reversal"):
        edge_triggers = by_edge.get(edge, [])
        if edge_triggers:
            last = edge_triggers[-1]
            last_time = last.timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
            print(
                f"{edge:<30} {len(edge_triggers):>8} {last.direction.upper():>12} "
                f"{last_time:>24} {last.entry:>12.2f} {'LIVE':>10}"
            )
        else:
            print(f"{edge:<30} {0:>8} {'WAITING':>12} {'-':>24} {'-':>12} {'ARMED':>10}")

    print("-" * 104)
    print(f"{'TOTAL SIGNALS':<30} {len(triggers):>8}")
    print("=" * 104)


def write_triggers(path: Path, triggers: list[EdgeTrigger]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "edge",
                "direction",
                "entry",
                "stop",
                "target",
                "qty",
                "risk_dollars",
                "stop_points",
                "target_r",
                "alert_message",
            ]
        )
        for trigger in triggers:
            writer.writerow(
                [
                    trigger.timestamp.isoformat(),
                    trigger.edge,
                    trigger.direction,
                    f"{trigger.entry:.6f}",
                    f"{trigger.stop:.6f}",
                    f"{trigger.target:.6f}",
                    f"{trigger.qty:.6f}",
                    f"{trigger.risk_dollars:.2f}",
                    f"{trigger.stop_points:.6f}",
                    f"{trigger.target_r:.2f}",
                    trigger.alert_message,
                ]
            )


def write_alerts(path: Path, triggers: list[EdgeTrigger]) -> None:
    with path.open("w") as f:
        for trigger in triggers:
            f.write(f"{trigger.timestamp.isoformat()} | {trigger.alert_message}\n")


def print_alerts(triggers: list[EdgeTrigger]) -> None:
    if not triggers:
        print("\nAlerts: none")
        return

    print("\nAlerts")
    print("-" * 104)
    for trigger in triggers:
        print(f"{trigger.timestamp:%Y-%m-%d %H:%M:%S %Z} | {trigger.alert_message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor NY Open trading edges from OHLCV CSV data.")
    parser.add_argument("csv_file", type=Path, help="Path to OHLCV CSV file.")
    parser.add_argument("--out", type=Path, default=Path("ny_open_edge_triggers.csv"), help="Output CSV for detected triggers.")
    parser.add_argument("--alerts-out", type=Path, default=Path("ny_open_edge_alerts.txt"), help="Output TXT file for alert messages.")
    parser.add_argument("--risk", type=float, default=1000.0, help="Dollar risk per setup.")
    parser.add_argument("--stop-points", type=float, default=50.0, help="Fixed stop loss in points.")
    parser.add_argument("--target-r", type=float, default=2.0, help="Take profit in R.")
    parser.add_argument("--point-value", type=float, default=1.0, help="Dollar value of one point for one contract/share/unit.")
    parser.add_argument(
        "--no-close-back-inside",
        action="store_true",
        help="For 9:30 sweep reversal, do not require close back inside the 9:30 candle range.",
    )
    args = parser.parse_args()

    candles = read_candles(args.csv_file)
    risk = RiskConfig(
        risk_dollars=args.risk,
        stop_points=args.stop_points,
        target_r=args.target_r,
        point_value=args.point_value,
        require_close_back_inside=not args.no_close_back_inside,
    )
    triggers = detect_edges(candles, risk)

    print_dashboard(triggers)
    print_alerts(triggers)
    write_triggers(args.out, triggers)
    write_alerts(args.alerts_out, triggers)
    print(f"\nSaved triggers to: {args.out}")
    print(f"Saved alerts to: {args.alerts_out}")


if __name__ == "__main__":
    main()
