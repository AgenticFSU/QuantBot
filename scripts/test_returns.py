import json
import csv
import os
import re
import datetime


print("Current working directory:", os.getcwd())
CSV_FILE = "scripts/stock_report.csv"

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
def update_actuals(date, previous_returns):
    """Update stock CSV with actual prices and returns."""
    rows = []
    with open(CSV_FILE, "r", newline="") as f:
        rows = list(csv.reader(f))

    # Map of (Date, Ticker) -> row index
    index_map = {(row[0], row[1]): i for i, row in enumerate(rows) if i > 0}

    for ticker, data in previous_returns.items():
        stock_data = data["Stock Data"]
        ohlc = stock_data["Daily OHLC (last 5 days)"].get(date)
        if ohlc:
            key = (date, ticker)
            if key in index_map:
                idx = index_map[key]
                open_price = ohlc["open"]
                close_price = ohlc["close"]
                intraday_return = ((close_price - open_price) / open_price) * 100
                rows[idx][2] = f"{open_price:.2f}"
                rows[idx][3] = f"{close_price:.2f}"
                rows[idx][5] = f"{intraday_return:.2f}%"
                print(f"Updated {ticker} on {date}: Open={open_price}, Close={close_price}, Return={intraday_return:.2f}%")
            else:
                print(f"Row for {ticker} on {date} not found in CSV")
        else:
            print(f"No OHLC data for {ticker} on {date}")


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

    trading_date = get_latest_date_from_previous_returns(previous_returns)
    print(f"Using trading date from data: {trading_date}")

    # BEFORE MARKET OPEN
    # RUN THE BOT PREDICTIONS how can we do this? ALSO WE HAVE TO WAIT LIKE 20mins for the bot to make the decision and then call the funct
    # As we have to wait until the ticker decision table gets created by the bot 
    append_predictions(trading_date, decisions)

    # AFTER MARKET CLOSE
    update_actuals(trading_date, previous_returns)

    print("✅ Stock decisions updated successfully.")



