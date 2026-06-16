"""DEPRECATED — has a data-leakage flaw; use scripts/evaluation_predictions.py.

This script scored a prediction using the SAME trading day's OHLC that informed
the decision (``trading_date`` was the latest date already present in
``previous_returns.md``). Evaluating tomorrow's call with today's known data is
look-ahead/data leakage.

The leakage-free evaluator is ``scripts/evaluation_predictions.py``, which
fetches fresh OHLC and scores strictly against a date AFTER the prediction date.
``update_actuals`` below now refuses to score when the target date is not
strictly after the prediction date.
"""

import json
import csv
import os
import re
import datetime
import warnings


print("Current working directory:", os.getcwd())
CSV_FILE = "scripts/stock_report.csv"

warnings.warn(
    "scripts/test_returns.py is deprecated due to data leakage; "
    "use scripts/evaluation_predictions.py instead.",
    DeprecationWarning,
    stacklevel=2,
)

# --- STEP 1: Initialize CSV file ---
def init_csv():
    """Create CSV file with headers if it doesn't exist."""
    if not os.path.exists(CSV_FILE):
        os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Ticker", "Open", "Close", "Decision", "Return"])

# --- STEP 2: Load decisions from markdown file ---
def load_decisions(md_path):
    """Load ticker decisions from a markdown file."""
    decisions = {}
    md_path = os.path.abspath(md_path)
    print("Decision file path:", md_path)

    if not os.path.exists(md_path):
        raise FileNotFoundError(f"Decision file not found: {md_path}")

    with open(md_path, "r") as f:
        lines = f.readlines()
        for line in lines[2:]:  # skip header and separator
            parts = [p.strip() for p in line.strip().split("|") if p.strip()]
            if len(parts) == 2:
                ticker, decision = parts
                decisions[ticker] = decision
    return decisions

# --- STEP 3: Extract JSON from markdown ---
def extract_json_from_markdown(md_path):
    """Extract stock data JSON from a markdown file."""
    md_path = os.path.abspath(md_path)
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"Previous returns file not found: {md_path}")

    with open(md_path, "r") as f:
        content = f.read()

    match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
    if not match:
        raise ValueError("No JSON block found in previous_returns.md")

    return json.loads(match.group(1))

# --- STEP 4: Append predictions before market open ---
def append_predictions(date, decisions):
    """Append bot decisions before market open, avoiding duplicates."""
    existing_records = set()

    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                key = (row["Date"], row["Ticker"])
                existing_records.add(key)

    with open(CSV_FILE, "a", newline="") as csvfile:
        fieldnames = ["Date", "Ticker", "Open", "Close", "Decision", "Return"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if os.stat(CSV_FILE).st_size == 0:  # write header if file is empty
            writer.writeheader()

        for ticker, decision in decisions.items():
            key = (date, ticker)
            if key not in existing_records:  # avoid duplicates
                writer.writerow({
                    "Date": date,
                    "Ticker": ticker,
                    "Open": "",
                    "Close": "",
                    "Decision": decision,
                    "Return": ""
                })

# --- STEP 5: Update actual OHLC and return after market close ---
def update_actuals(prediction_date, target_date, previous_returns):
    """Update stock CSV with actual prices/returns for the TARGET date.

    Leakage guard: ``target_date`` must be strictly after ``prediction_date``.
    Scoring a prediction with same-day (or earlier) data is look-ahead bias, so
    in that case we refuse and direct callers to evaluation_predictions.py.
    """
    if not (target_date > prediction_date):
        warnings.warn(
            f"Refusing to score: target_date ({target_date}) is not strictly "
            f"after prediction_date ({prediction_date}). This would be data "
            f"leakage. Use scripts/evaluation_predictions.py to fetch and score "
            f"the next trading day's OHLC.",
            stacklevel=2,
        )
        return

    rows = []
    with open(CSV_FILE, "r", newline="") as f:
        rows = list(csv.reader(f))

    # Map of (Date, Ticker) -> row index
    index_map = {(row[0], row[1]): i for i, row in enumerate(rows) if i > 0}

    for ticker, data in previous_returns.items():
        stock_data = data["Stock Data"]
        ohlc = stock_data["Daily OHLC (last 5 days)"].get(target_date)
        if ohlc:
            key = (target_date, ticker)
            if key in index_map:
                idx = index_map[key]
                open_price = ohlc["open"]
                close_price = ohlc["close"]
                intraday_return = ((close_price - open_price) / open_price) * 100
                rows[idx][2] = f"{open_price:.2f}"
                rows[idx][3] = f"{close_price:.2f}"
                rows[idx][5] = f"{intraday_return:.2f}%"
                print(f"Updated {ticker} on {target_date}: Open={open_price}, Close={close_price}, Return={intraday_return:.2f}%")
            else:
                print(f"Row for {ticker} on {target_date} not found in CSV")
        else:
            print(f"No OHLC data for {ticker} on {target_date}")


    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def get_latest_date_from_previous_returns(previous_returns):
    """Find the latest date available across all tickers in previous_returns JSON."""
    all_dates = set()
    for ticker, data in previous_returns.items():
        dates = data["Stock Data"]["Daily OHLC (last 5 days)"].keys()
        all_dates.update(dates)
    return max(all_dates)


# --- MAIN ---
#The main issue here is that we had to wait 12 hours or whatever time until the market closes to append the decision
# Another way we could do it is run the script only for the AV api intraday results and then append it at the end of the day 
# But thsi way it wouldnt be so dynamic the code as we would have to input all of the stocks 
if __name__ == "__main__":
    #Also we can change the stocks to run in different stocks 
    init_csv()

    decisions = load_decisions("data/generated/TickerDecisionTable.md")
    previous_returns = extract_json_from_markdown("data/generated/previous_returns.md")

    prediction_date = get_latest_date_from_previous_returns(previous_returns)
    print(f"Using prediction date from data: {prediction_date}")

    # BEFORE MARKET OPEN: record the bot's predictions for the NEXT trading day.
    append_predictions(prediction_date, decisions)

    # AFTER MARKET CLOSE: scoring is NOT done here — previous_returns.md does not
    # contain next-day OHLC and same-day scoring would be data leakage. Use
    # evaluation_predictions.py after the target trading day has closed.
    print(
        "Predictions recorded. To score them without data leakage, run:\n"
        "  python scripts/evaluation_predictions.py --prediction-date "
        f"{prediction_date}"
    )



