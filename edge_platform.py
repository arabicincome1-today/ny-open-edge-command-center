#!/usr/bin/env python3
"""
NY Open Edge Platform

Local web app for scanning NY Open trading edges.
Run:
    python3 edge_platform.py
Open:
    http://127.0.0.1:8765
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ny_open_edge_dashboard import RiskConfig, detect_edges, read_candles


ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8765


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NY Open Edge Platform</title>
  <style>
    :root {
      --bg: #090b10;
      --panel: #111821;
      --panel-2: #141f2c;
      --line: #243244;
      --text: #edf3f8;
      --muted: #8ea0b4;
      --green: #41d98d;
      --red: #ff5f6d;
      --blue: #58a6ff;
      --gold: #f7b84b;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 15% 0%, rgba(88, 166, 255, 0.16), transparent 30rem),
        radial-gradient(circle at 80% 8%, rgba(65, 217, 141, 0.12), transparent 24rem),
        linear-gradient(180deg, #0d1117 0%, var(--bg) 45%, #06070a 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .shell {
      width: min(1200px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 28px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .mark {
      width: 42px;
      height: 42px;
      border: 1px solid rgba(88, 166, 255, 0.38);
      background: linear-gradient(135deg, rgba(88, 166, 255, 0.28), rgba(65, 217, 141, 0.18));
      display: grid;
      place-items: center;
      border-radius: 8px;
      font-weight: 800;
      letter-spacing: 0;
      color: white;
      box-shadow: 0 12px 40px rgba(88, 166, 255, 0.15);
    }

    h1, h2, h3, p { margin: 0; }
    h1 { font-size: 24px; line-height: 1.1; }
    .subtle { color: var(--muted); font-size: 13px; margin-top: 5px; }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid rgba(65, 217, 141, 0.35);
      color: var(--green);
      background: rgba(65, 217, 141, 0.08);
      padding: 8px 11px;
      border-radius: 999px;
      font-size: 13px;
      white-space: nowrap;
    }

    .dot {
      width: 7px;
      height: 7px;
      background: var(--green);
      border-radius: 50%;
      box-shadow: 0 0 14px var(--green);
    }

    .grid {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 18px;
      align-items: start;
    }

    .card {
      border: 1px solid var(--line);
      background: rgba(17, 24, 33, 0.88);
      border-radius: 8px;
      box-shadow: 0 18px 60px rgba(0, 0, 0, 0.28);
      overflow: hidden;
    }

    .card-head {
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .card-head h2 { font-size: 15px; }
    .card-body { padding: 18px; }

    label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 7px;
    }

    input, select {
      width: 100%;
      height: 40px;
      border: 1px solid #2a3a4f;
      background: #0c1118;
      color: var(--text);
      border-radius: 7px;
      padding: 0 11px;
      outline: none;
      font: inherit;
    }

    input:focus, select:focus { border-color: var(--blue); }

    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .field { margin-bottom: 14px; }

    button {
      width: 100%;
      height: 42px;
      border: 0;
      border-radius: 7px;
      color: #04120b;
      background: linear-gradient(135deg, var(--green), #8af7ba);
      font-weight: 800;
      cursor: pointer;
      box-shadow: 0 14px 30px rgba(65, 217, 141, 0.16);
    }

    button:disabled {
      opacity: 0.55;
      cursor: progress;
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }

    .metric {
      padding: 15px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(20, 31, 44, 0.9), rgba(12, 17, 24, 0.95));
      border-radius: 8px;
      min-height: 86px;
    }

    .metric span {
      color: var(--muted);
      font-size: 12px;
    }

    .metric strong {
      display: block;
      font-size: 24px;
      margin-top: 9px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    th, td {
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      white-space: nowrap;
    }

    th {
      color: var(--muted);
      font-weight: 600;
      background: rgba(20, 31, 44, 0.65);
    }

    .side {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 58px;
      height: 24px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 800;
    }

    .long { background: rgba(65, 217, 141, 0.12); color: var(--green); }
    .short { background: rgba(255, 95, 109, 0.12); color: var(--red); }

    .alerts {
      display: grid;
      gap: 10px;
      max-height: 230px;
      overflow: auto;
    }

    .alert {
      border: 1px solid var(--line);
      background: #0c1118;
      border-left: 3px solid var(--gold);
      border-radius: 7px;
      padding: 11px 12px;
      color: #dce7f2;
      font-size: 13px;
      line-height: 1.45;
    }

    .roadmap {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }

    .module {
      border: 1px solid var(--line);
      background: rgba(12, 17, 24, 0.86);
      border-radius: 8px;
      padding: 14px;
    }

    .module b { font-size: 13px; }
    .module p {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      margin-top: 7px;
    }

    .empty {
      color: var(--muted);
      padding: 32px;
      text-align: center;
      border: 1px dashed #304259;
      border-radius: 8px;
      background: rgba(12, 17, 24, 0.45);
    }

    textarea {
      width: 100%;
      min-height: 92px;
      resize: vertical;
      border: 1px solid #2a3a4f;
      background: #0c1118;
      color: var(--text);
      border-radius: 7px;
      padding: 11px;
      outline: none;
      font: inherit;
      line-height: 1.45;
    }

    textarea:focus { border-color: var(--blue); }

    .answer {
      margin-top: 12px;
      border: 1px solid var(--line);
      background: #0c1118;
      border-radius: 8px;
      padding: 14px;
      color: #dce7f2;
      white-space: pre-wrap;
      line-height: 1.5;
      font-size: 13px;
    }

    @media (max-width: 920px) {
      .grid { grid-template-columns: 1fr; }
      .metrics, .roadmap { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      header { align-items: flex-start; flex-direction: column; }
    }

    @media (max-width: 560px) {
      .metrics, .roadmap, .form-grid { grid-template-columns: 1fr; }
      th, td { white-space: normal; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div class="brand">
        <div class="mark">NY</div>
        <div>
          <h1>NY Open Edge Platform</h1>
          <p class="subtle">Signals, risk, alerts, and edge research in one daily cockpit.</p>
        </div>
      </div>
      <div class="status-pill"><span class="dot"></span><span id="platformStatus">Local platform online</span></div>
    </header>

    <section class="grid">
      <aside class="card">
        <div class="card-head">
          <h2>Scan Controls</h2>
          <span class="subtle">NQ defaults</span>
        </div>
        <div class="card-body">
          <div class="field">
            <label>Data Source</label>
            <select id="source">
              <option value="sample">Sample candles</option>
              <option value="csv">Local CSV path</option>
              <option value="download">Download from Yahoo</option>
            </select>
          </div>

          <div class="field" id="csvField">
            <label>CSV Path</label>
            <input id="csvPath" value="sample_candles.csv" />
          </div>

          <div id="downloadFields">
            <div class="form-grid">
              <div class="field">
                <label>Symbol</label>
                <input id="symbol" value="NQ=F" />
              </div>
              <div class="field">
                <label>Interval</label>
                <input id="interval" value="1m" />
              </div>
            </div>
            <div class="form-grid">
              <div class="field">
                <label>Period</label>
                <input id="period" value="5d" />
              </div>
              <div class="field">
                <label>Output CSV</label>
                <input id="out" value="NQ_1m.csv" />
              </div>
            </div>
          </div>

          <div class="form-grid">
            <div class="field">
              <label>Risk $</label>
              <input id="risk" type="number" value="1000" />
            </div>
            <div class="field">
              <label>Stop Points</label>
              <input id="stopPoints" type="number" value="50" />
            </div>
          </div>

          <div class="form-grid">
            <div class="field">
              <label>Target R</label>
              <input id="targetR" type="number" value="2" step="0.25" />
            </div>
            <div class="field">
              <label>Point Value</label>
              <input id="pointValue" type="number" value="20" />
            </div>
          </div>

          <button id="scanButton">Run Edge Scan</button>
          <p class="subtle" id="scanNote" style="margin-top: 12px;">Use sample first, then switch to real downloaded candles.</p>
        </div>
      </aside>

      <section>
        <div class="metrics">
          <div class="metric"><span>Total Signals</span><strong id="totalSignals">0</strong></div>
          <div class="metric"><span>Long Signals</span><strong id="longSignals">0</strong></div>
          <div class="metric"><span>Short Signals</span><strong id="shortSignals">0</strong></div>
          <div class="metric"><span>Last Edge</span><strong id="lastEdge" style="font-size: 17px;">None</strong></div>
        </div>

        <div class="card">
          <div class="card-head">
            <h2>Signals</h2>
            <span class="subtle" id="datasetLabel">No scan yet</span>
          </div>
          <div class="card-body" style="padding: 0;">
            <div style="overflow-x: auto;">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Edge</th>
                    <th>Side</th>
                    <th>Entry</th>
                    <th>Stop</th>
                    <th>Target</th>
                    <th>Qty</th>
                  </tr>
                </thead>
                <tbody id="signalsBody">
                  <tr><td colspan="7"><div class="empty">Run a scan to load signals.</div></td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="card" style="margin-top: 18px;">
          <div class="card-head">
            <h2>Alerts</h2>
            <span class="subtle">Copy-ready messages</span>
          </div>
          <div class="card-body">
            <div class="alerts" id="alertsBody">
              <div class="empty">No alerts yet.</div>
            </div>
          </div>
        </div>

        <div class="card" style="margin-top: 18px;">
          <div class="card-head">
            <h2>Ask The Machine</h2>
            <span class="subtle">Probabilities + technicals</span>
          </div>
          <div class="card-body">
            <textarea id="question">What are the technicals and probabilities right now?</textarea>
            <button id="askButton" style="margin-top: 12px;">Ask</button>
            <div class="answer" id="answerBox">Run a scan, then ask about the latest candles.</div>
          </div>
        </div>

        <div class="roadmap">
          <div class="module"><b>Backtest Lab</b><p>Next: label TP/SL outcomes and rank every setup by R.</p></div>
          <div class="module"><b>Edge Library</b><p>Add Setup 3, Setup 4, and toggle each edge on or off.</p></div>
          <div class="module"><b>ML Filter</b><p>Score signals after the dataset has enough trade outcomes.</p></div>
          <div class="module"><b>Live API</b><p>Later: connect broker/data feed for NY Open live alerts.</p></div>
        </div>
      </section>
    </section>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);

    function syncSourceFields() {
      const source = $("source").value;
      $("csvField").style.display = source === "download" ? "none" : "block";
      $("downloadFields").style.display = source === "download" ? "block" : "none";
      if (source === "sample") $("csvPath").value = "sample_candles.csv";
    }

    $("source").addEventListener("change", syncSourceFields);
    syncSourceFields();

    function money(value) {
      return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
    }

    function render(data) {
      $("totalSignals").textContent = data.summary.total;
      $("longSignals").textContent = data.summary.long;
      $("shortSignals").textContent = data.summary.short;
      $("lastEdge").textContent = data.summary.last_edge || "None";
      $("datasetLabel").textContent = data.dataset;

      if (!data.triggers.length) {
        $("signalsBody").innerHTML = '<tr><td colspan="7"><div class="empty">No signals found for this dataset.</div></td></tr>';
        $("alertsBody").innerHTML = '<div class="empty">No alerts generated.</div>';
        return;
      }

      $("signalsBody").innerHTML = data.triggers.map((t) => `
        <tr>
          <td>${t.timestamp}</td>
          <td>${t.edge}</td>
          <td><span class="side ${t.direction}">${t.direction.toUpperCase()}</span></td>
          <td>${money(t.entry)}</td>
          <td>${money(t.stop)}</td>
          <td>${money(t.target)}</td>
          <td>${money(t.qty)}</td>
        </tr>
      `).join("");

      $("alertsBody").innerHTML = data.triggers.map((t) => `
        <div class="alert">${t.alert_message}</div>
      `).join("");
    }

    async function runScan() {
      const button = $("scanButton");
      button.disabled = true;
      button.textContent = "Scanning...";
      $("scanNote").textContent = "Working through candles and edge rules.";

      const params = new URLSearchParams({
        source: $("source").value,
        csv: $("csvPath").value,
        symbol: $("symbol").value,
        interval: $("interval").value,
        period: $("period").value,
        out: $("out").value,
        risk: $("risk").value,
        stop_points: $("stopPoints").value,
        target_r: $("targetR").value,
        point_value: $("pointValue").value
      });

      try {
        const response = await fetch(`/api/scan?${params.toString()}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Scan failed");
        render(data);
        $("scanNote").textContent = "Scan complete.";
      } catch (error) {
        $("scanNote").textContent = error.message;
      } finally {
        button.disabled = false;
        button.textContent = "Run Edge Scan";
      }
    }

    async function askMachine() {
      const button = $("askButton");
      button.disabled = true;
      button.textContent = "Thinking...";

      const params = new URLSearchParams({
        source: $("source").value,
        csv: $("csvPath").value,
        symbol: $("symbol").value,
        interval: $("interval").value,
        period: $("period").value,
        out: $("out").value,
        risk: $("risk").value,
        stop_points: $("stopPoints").value,
        target_r: $("targetR").value,
        point_value: $("pointValue").value,
        question: $("question").value
      });

      try {
        const response = await fetch(`/api/ask?${params.toString()}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Ask failed");
        $("answerBox").textContent = data.answer;
      } catch (error) {
        $("answerBox").textContent = error.message;
      } finally {
        button.disabled = false;
        button.textContent = "Ask";
      }
    }

    $("scanButton").addEventListener("click", runScan);
    $("askButton").addEventListener("click", askMachine);
    runScan();
  </script>
</body>
</html>
"""


def sma(values: list[float], length: int) -> float | None:
    if len(values) < length:
        return None
    return sum(values[-length:]) / length


def rsi(values: list[float], length: int = 14) -> float | None:
    if len(values) <= length:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for current, previous in zip(values[-length:], values[-length - 1 : -1]):
        change = current - previous
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))
    avg_gain = sum(gains) / length
    avg_loss = sum(losses) / length
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(candles: list, length: int = 14) -> float | None:
    if len(candles) <= length:
        return None
    true_ranges: list[float] = []
    previous_close = candles[-length - 1].close
    for candle in candles[-length:]:
        true_range = max(candle.high - candle.low, abs(candle.high - previous_close), abs(candle.low - previous_close))
        true_ranges.append(true_range)
        previous_close = candle.close
    return sum(true_ranges) / length


def latest_opening_range(candles: list) -> tuple[float | None, float | None]:
    if not candles:
        return None, None
    latest_date = candles[-1].ny_date
    day_candles = [candle for candle in candles if candle.ny_date == latest_date]
    opening_range = [candle for candle in day_candles if candle.ny_time.hour == 9 and 30 <= candle.ny_time.minute < 45]
    if not opening_range:
        return None, None
    return max(candle.high for candle in opening_range), min(candle.low for candle in opening_range)


def answer_question(question: str, candles: list, triggers: list) -> str:
    if not candles:
        return "I do not have candles loaded yet. Download or load a CSV first."

    closes = [candle.close for candle in candles]
    last = candles[-1]
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    rsi14 = rsi(closes, 14)
    atr14 = atr(candles, 14)
    or_high, or_low = latest_opening_range(candles)
    q = question.lower()

    long_count = sum(1 for trigger in triggers if trigger.direction == "long")
    short_count = sum(1 for trigger in triggers if trigger.direction == "short")
    orb_count = sum(1 for trigger in triggers if trigger.edge == "Opening Range Break")
    sweep_count = sum(1 for trigger in triggers if trigger.edge == "9:30 Sweep Reversal")

    trend = "neutral"
    if sma20 is not None:
        trend = "bullish above 20 SMA" if last.close > sma20 else "bearish below 20 SMA"
    if sma20 is not None and sma50 is not None:
        if last.close > sma20 > sma50:
            trend = "bullish trend stack: close > 20 SMA > 50 SMA"
        elif last.close < sma20 < sma50:
            trend = "bearish trend stack: close < 20 SMA < 50 SMA"

    lines = [
        f"Latest candle: {last.ny_time:%Y-%m-%d %H:%M:%S %Z}",
        f"Last close: {last.close:.2f}",
        f"Current read: {trend}",
    ]

    if rsi14 is not None:
        rsi_state = "overbought" if rsi14 >= 70 else "oversold" if rsi14 <= 30 else "balanced"
        lines.append(f"RSI 14: {rsi14:.1f} ({rsi_state})")
    if atr14 is not None:
        lines.append(f"ATR 14: {atr14:.2f} points")
    if or_high is not None and or_low is not None:
        location = "inside"
        if last.close > or_high:
            location = "above"
        elif last.close < or_low:
            location = "below"
        lines.append(f"Latest opening range: high {or_high:.2f}, low {or_low:.2f}. Price is {location} the range.")

    if "prob" in q or "chance" in q or "odds" in q or "edge" in q:
        lines.extend(
            [
                "",
                "Probability note:",
                f"I found {len(triggers)} historical signals in the loaded candles: {long_count} long, {short_count} short.",
                f"By edge: ORB {orb_count}, 9:30 Sweep {sweep_count}.",
                "This is signal frequency, not win probability yet. To give true odds, we need the outcome labeler: TP hit before SL, result in R, MFE, and MAE.",
            ]
        )

    if "technical" in q or "right now" in q or "trend" in q or "rsi" in q or "atr" in q:
        lines.extend(
            [
                "",
                "Technical take:",
                "Bias is based on the latest loaded candle file, not a broker-grade live feed.",
                "For live answers during NY Open, the next upgrade is a broker/data API connector.",
            ]
        )

    if "next" in q or "build" in q or "missing" in q:
        lines.extend(
            [
                "",
                "What is missing next:",
                "1. Outcome labeler for real win probabilities.",
                "2. More edge detectors.",
                "3. Live data API so the machine updates without manual downloads.",
                "4. ML filter after enough labeled trades exist.",
            ]
        )

    return "\n".join(lines)


def download_yahoo_candles(symbol: str, interval: str, period: str, out: Path) -> Path:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("Missing dependency: run python3 -m pip install -r requirements.txt") from exc

    data = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False, prepost=True)
    if data.empty:
        raise RuntimeError(f"No candles returned for {symbol}. Try another symbol, interval, or period.")

    data = data.reset_index()
    timestamp_col = "Datetime" if "Datetime" in data.columns else "Date"

    if hasattr(data.columns, "get_level_values") and len(data.columns.names) > 1:
        data.columns = [str(col[0]).lower() if isinstance(col, tuple) else str(col).lower() for col in data.columns]
        timestamp_col = "datetime" if "datetime" in data.columns else "date"
    else:
        data.columns = [str(col).lower() for col in data.columns]
        timestamp_col = timestamp_col.lower()

    data = data.rename(columns={timestamp_col: "timestamp"})
    required = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise RuntimeError(f"Downloaded data is missing columns: {', '.join(missing)}")

    data[required].dropna(subset=["open", "high", "low", "close"]).to_csv(out, index=False)
    return out


def trigger_to_dict(trigger) -> dict:
    row = asdict(trigger)
    row["timestamp"] = trigger.timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")
    return row


def write_outputs(triggers: list, triggers_path: Path, alerts_path: Path) -> None:
    with triggers_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "edge", "direction", "entry", "stop", "target", "qty", "alert_message"])
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
                    trigger.alert_message,
                ]
            )

    with alerts_path.open("w") as f:
        for trigger in triggers:
            f.write(f"{trigger.timestamp.isoformat()} | {trigger.alert_message}\n")


class PlatformHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_html(INDEX_HTML)
            return

        if parsed.path == "/api/scan":
            self.handle_scan(parse_qs(parsed.query))
            return

        if parsed.path == "/api/ask":
            self.handle_ask(parse_qs(parsed.query))
            return

        self.send_json({"error": "Not found"}, status=404)

    def resolve_dataset(self, params: dict[str, list[str]]) -> tuple[Path, str]:
        source = self.param(params, "source", "sample")
        if source == "download":
            symbol = self.param(params, "symbol", "NQ=F")
            interval = self.param(params, "interval", "1m")
            period = self.param(params, "period", "5d")
            out = ROOT / self.param(params, "out", "NQ_1m.csv")
            csv_path = download_yahoo_candles(symbol, interval, period, out)
            return csv_path, f"{symbol} {interval} {period} -> {csv_path.name}"

        csv_name = "sample_candles.csv" if source == "sample" else self.param(params, "csv", "sample_candles.csv")
        csv_path = Path(csv_name)
        if not csv_path.is_absolute():
            csv_path = ROOT / csv_path
        return csv_path, csv_path.name

    def resolve_risk(self, params: dict[str, list[str]]) -> RiskConfig:
        return RiskConfig(
            risk_dollars=float(self.param(params, "risk", "1000")),
            stop_points=float(self.param(params, "stop_points", "50")),
            target_r=float(self.param(params, "target_r", "2")),
            point_value=float(self.param(params, "point_value", "20")),
            require_close_back_inside=True,
        )

    def handle_scan(self, params: dict[str, list[str]]) -> None:
        try:
            risk = self.resolve_risk(params)
            csv_path, dataset = self.resolve_dataset(params)
            candles = read_candles(csv_path)
            triggers = detect_edges(candles, risk)
            write_outputs(triggers, ROOT / "ny_open_edge_triggers.csv", ROOT / "ny_open_edge_alerts.txt")

            payload = {
                "dataset": dataset,
                "summary": {
                    "total": len(triggers),
                    "long": sum(1 for trigger in triggers if trigger.direction == "long"),
                    "short": sum(1 for trigger in triggers if trigger.direction == "short"),
                    "last_edge": triggers[-1].edge if triggers else "None",
                },
                "triggers": [trigger_to_dict(trigger) for trigger in triggers],
            }
            self.send_json(payload)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def handle_ask(self, params: dict[str, list[str]]) -> None:
        try:
            risk = self.resolve_risk(params)
            csv_path, dataset = self.resolve_dataset(params)
            candles = read_candles(csv_path)
            triggers = detect_edges(candles, risk)
            question = self.param(params, "question", "What are the technicals and probabilities right now?")
            answer = answer_question(question, candles, triggers)
            self.send_json({"dataset": dataset, "answer": answer})
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    @staticmethod
    def param(params: dict[str, list[str]], name: str, default: str) -> str:
        values = params.get(name)
        return values[0] if values and values[0] else default

    def send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", DEFAULT_PORT), PlatformHandler)
    print(f"NY Open Edge Platform running at http://127.0.0.1:{DEFAULT_PORT}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
