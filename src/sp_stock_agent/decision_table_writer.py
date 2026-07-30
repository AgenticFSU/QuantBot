"""Deterministically build ``TickerDecisionTable.csv`` from the final report.

This replaces the former ``decision_parser`` agent: instead of spending an LLM
call to reformat the final decision, the ``final_decision`` agent is prompted to
end its report with a machine-readable ``csv`` block, and this module parses it.

Extraction order:
  1. The last fenced ``csv`` block whose header starts with ``Ticker``.
  2. Fallback: any markdown table row whose first cell looks like a ticker.

Output is a CSV file with the run metadata folded in as leading columns:
``RunDate,DataCollectedThrough,PredictionDate,Ticker,Decision,Open,Close,
IntradayReturn,Rationale``. The ``Open``/``Close`` (from the ``**OHLC:**`` line),
``IntradayReturn`` and ``Rationale`` values are pulled from each ticker's
``### TICKER`` subsection in the final report, not from the trailing csv block.
Downstream evaluation scripts read it with ``csv.DictReader``.
"""

import csv
import io
import re
from pathlib import Path
from typing import List, Optional, Tuple

FINANCIAL_REPORT = "data/generated/financial_report.md"
OUTPUT_TABLE = "data/generated/TickerDecisionTable.csv"

# Column order for the generated decision table CSV. The run metadata that used
# to live in a markdown header is now folded in as leading columns so the file
# is a single, self-describing table.
CSV_FIELDS = [
    "RunDate",
    "DataCollectedThrough",
    "PredictionDate",
    "Ticker",
    "Decision",
    "Open",
    "Close",
    "IntradayReturn",
    "Rationale",
]

# Fenced block: ```csv\nTicker,...\n...\n```  (the ```csv tag is optional)
_CSV_BLOCK_RE = re.compile(
    r"```(?:csv)?\s*\n(Ticker.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)
_TICKER_RE = re.compile(r"^[A-Za-z][A-Za-z.\-]{0,5}$")

# Per-ticker subsection heading: ``### AAPL (Apple Inc.)`` — capture the ticker.
_TICKER_HEADING_RE = re.compile(r"^#{3,}\s+([A-Za-z][A-Za-z.\-]{0,5})\b")
# Bold field lines within a subsection, e.g. ``- **Intraday Return:** +1.2%``.
_INTRADAY_RE = re.compile(r"\*\*\s*Intraday Return\s*:?\s*\*\*\s*(.+)", re.IGNORECASE)
_RATIONALE_RE = re.compile(r"\*\*\s*Rationale\s*:?\s*\*\*\s*(.+)", re.IGNORECASE)
_OHLC_RE = re.compile(r"\*\*\s*OHLC\s*:?\s*\*\*\s*(.+)", re.IGNORECASE)
# Individual O:/C: values within the OHLC line, e.g. ``O: 210.0`` / ``C: 211.5``.
_OPEN_RE = re.compile(r"\bO\s*:\s*([^,]+)", re.IGNORECASE)
_CLOSE_RE = re.compile(r"\bC\s*:\s*([^,]+)", re.IGNORECASE)


def _parse_csv_block(text: str) -> List[Tuple[str, str]]:
    """Parse the LAST fenced csv block that begins with a ``Ticker`` header."""
    matches = list(_CSV_BLOCK_RE.finditer(text))
    if not matches:
        return []
    block = matches[-1].group(1)
    out: List[Tuple[str, str]] = []
    for row in csv.DictReader(io.StringIO(block)):
        norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        ticker = norm.get("ticker")
        decision = norm.get("decision")
        if ticker and decision:
            out.append((ticker.upper(), decision))
    return out


def _parse_markdown_table(text: str) -> List[Tuple[str, str]]:
    """Fallback: scan markdown table rows for ``ticker | decision`` pairs."""
    results: List[Tuple[str, str]] = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        first = cells[0]
        if first.lower() in ("ticker", "tickers"):
            continue
        if set(first) <= set("-: "):  # separator row
            continue
        if _TICKER_RE.match(first):
            results.append((first.upper(), cells[1]))
    return results


def extract_decisions(report_text: str) -> List[Tuple[str, str]]:
    """Extract (ticker, decision) pairs from the final decision report."""
    return _parse_csv_block(report_text) or _parse_markdown_table(report_text)


def extract_ticker_details(report_text: str) -> dict:
    """Map ``TICKER`` -> details dict parsed from the report body.

    Each entry has ``open``/``close`` (from the ``**OHLC:**`` line),
    ``intraday_return`` and ``rationale`` (from their respective bold fields in
    the ``### TICKER`` subsection). Missing fields yield empty strings.
    """
    details: dict = {}
    current: Optional[str] = None
    for line in report_text.splitlines():
        heading = _TICKER_HEADING_RE.match(line.strip())
        if heading:
            current = heading.group(1).upper()
            details.setdefault(
                current,
                {"open": "", "close": "", "intraday_return": "", "rationale": ""},
            )
            continue
        if current is None:
            continue
        m = _OHLC_RE.search(line)
        if m:
            ohlc = m.group(1)
            open_m = _OPEN_RE.search(ohlc)
            close_m = _CLOSE_RE.search(ohlc)
            if open_m:
                details[current]["open"] = open_m.group(1).strip()
            if close_m:
                details[current]["close"] = close_m.group(1).strip()
            continue
        m = _INTRADAY_RE.search(line)
        if m:
            details[current]["intraday_return"] = m.group(1).strip()
            continue
        m = _RATIONALE_RE.search(line)
        if m:
            details[current]["rationale"] = m.group(1).strip()
    return details


def write_decision_table(
    report_path: str = FINANCIAL_REPORT,
    output_path: str = OUTPUT_TABLE,
    *,
    current_date: Optional[str] = None,
    market_data_date: Optional[str] = None,
    prediction_date: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Read the final report and write the decision table as CSV.

    The run metadata (``current_date``/``market_data_date``/``prediction_date``)
    is written into the leading ``RunDate``/``DataCollectedThrough``/
    ``PredictionDate`` columns; when not provided those cells are left blank.

    Returns the list of extracted ``(ticker, decision)`` pairs.
    """
    p = Path(report_path)
    if not p.exists():
        raise FileNotFoundError(f"Final decision report not found: {report_path}")

    report_text = p.read_text()
    decisions = extract_decisions(report_text)
    details = extract_ticker_details(report_text)

    run_date = current_date or ""
    data_through = market_data_date or ""
    pred_date = prediction_date or ""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for ticker, decision in decisions:
            info = details.get(ticker.upper(), {})
            writer.writerow(
                {
                    "RunDate": run_date,
                    "DataCollectedThrough": data_through,
                    "PredictionDate": pred_date,
                    "Ticker": ticker,
                    "Decision": decision,
                    "Open": info.get("open", ""),
                    "Close": info.get("close", ""),
                    "IntradayReturn": info.get("intraday_return", ""),
                    "Rationale": info.get("rationale", ""),
                }
            )
    return decisions


if __name__ == "__main__":
    extracted = write_decision_table()
    print(f"Wrote {len(extracted)} decision(s) to {OUTPUT_TABLE}")
