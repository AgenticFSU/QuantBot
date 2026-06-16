"""Evaluate QuantBot predictions against the NEXT trading day's intraday move.

This is the leakage-free replacement for the evaluation half of
``scripts/test_returns.py``. The bot makes a decision on a *prediction date* for
the *next* trading day's intraday move (open -> close). This script must run
AFTER that next trading day's market close: it fetches fresh OHLC from Alpha
Vantage and scores the decision strictly against a date that is *after* the
prediction date, so no information from the day the decision was made (or
earlier) leaks into the evaluation.

Run:
    python scripts/evaluation_predictions.py --prediction-date 2026-06-15

Scoring:
    "Invest"     is correct when the next-day intraday return  > 0.
    "Not invest" is correct when the next-day intraday return <= 0.
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# Make the package importable when run as a standalone script.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

from sp_stock_agent.tools.alpha_vantage_api_tool import FetchStockSummaryTool  # noqa: E402

DECISION_TABLE = "data/generated/TickerDecisionTable.md"
RESULTS_CSV = "scripts/evaluation_results.csv"
RESULT_FIELDS = [
    "PredictionDate",
    "TargetDate",
    "Ticker",
    "Decision",
    "Open",
    "Close",
    "IntradayReturnPct",
    "Correct",
]


def load_decisions(path: str) -> dict:
    """Parse the two-column ``| Ticker | Decision |`` markdown table."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Decision table not found: {path}")

    decisions = {}
    for line in p.read_text().splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0].lower() in ("ticker", "tickers"):
            continue
        if set(cells[0]) <= set("-: "):  # separator row
            continue
        decisions[cells[0].upper()] = cells[1]
    return decisions


def decision_is_correct(decision: str, intraday_return: float) -> bool:
    invest = decision.strip().lower() in ("invest", "buy", "yes")
    return intraday_return > 0 if invest else intraday_return <= 0


def _next_trading_date(daily_data: dict, prediction_date):
    """Return the earliest available date strictly AFTER the prediction date.

    Returns ``(date_str, ohlc)`` or ``(None, None)`` if next-day data is not
    available yet. This guard is what prevents same-day data leakage.
    """
    parsed = {}
    for date_str, ohlc in daily_data.items():
        try:
            parsed[datetime.strptime(date_str, "%Y-%m-%d").date()] = (date_str, ohlc)
        except ValueError:
            continue
    future = sorted(d for d in parsed if d > prediction_date)
    if not future:
        return None, None
    return parsed[future[0]]


def _append_results(path: str, rows: list) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    write_header = not p.exists() or p.stat().st_size == 0
    with open(p, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--prediction-date",
        required=True,
        help="YYYY-MM-DD: the date the bot made its decision (for the NEXT day).",
    )
    ap.add_argument("--decision-table", default=DECISION_TABLE)
    ap.add_argument("--results", default=RESULTS_CSV)
    args = ap.parse_args(argv)

    try:
        prediction_date = datetime.strptime(args.prediction_date, "%Y-%m-%d").date()
    except ValueError:
        print("--prediction-date must be YYYY-MM-DD", file=sys.stderr)
        return 1

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        print("ALPHA_VANTAGE_API_KEY is not set.", file=sys.stderr)
        return 1

    decisions = load_decisions(args.decision_table)
    if not decisions:
        print("No decisions found in the decision table.", file=sys.stderr)
        return 1

    tool = FetchStockSummaryTool()
    rows = []
    correct_count = 0
    scored = 0

    for ticker, decision in decisions.items():
        data = tool.fetch_single_stock(ticker, api_key)
        if not data or not data.get("daily_data"):
            print(f"{ticker}: no OHLC data available, skipping.")
            continue

        target_date_str, ohlc = _next_trading_date(data["daily_data"], prediction_date)
        if not target_date_str:
            print(
                f"{ticker}: next-day data after {prediction_date} not available yet, "
                f"skipping (run again after the next market close)."
            )
            continue

        open_price = ohlc["open"]
        close_price = ohlc["close"]
        intraday_return = (close_price - open_price) / open_price * 100
        correct = decision_is_correct(decision, intraday_return)
        scored += 1
        correct_count += int(correct)

        rows.append(
            {
                "PredictionDate": args.prediction_date,
                "TargetDate": target_date_str,
                "Ticker": ticker,
                "Decision": decision,
                "Open": f"{open_price:.2f}",
                "Close": f"{close_price:.2f}",
                "IntradayReturnPct": f"{intraday_return:.2f}",
                "Correct": correct,
            }
        )
        print(
            f"{ticker}: {decision} | target {target_date_str} | "
            f"return {intraday_return:.2f}% | {'correct' if correct else 'wrong'}"
        )

    if rows:
        _append_results(args.results, rows)
        accuracy = correct_count / scored * 100 if scored else 0.0
        print(f"\nScored {scored} prediction(s); accuracy {accuracy:.1f}%.")
        print(f"Appended results to {args.results}")
    else:
        print("\nNothing scored (next-day data not available yet).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
