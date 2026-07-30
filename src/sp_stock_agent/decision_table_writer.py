"""Deterministically build ``TickerDecisionTable.csv`` from the final report.

This replaces the former ``decision_parser`` agent: instead of spending an LLM
call to reformat the final decision, the ``final_decision`` agent is prompted to
end its report with a machine-readable ``csv`` block, and this module parses it.

Extraction order:
  1. The last fenced ``csv`` block whose header starts with ``Ticker``.
  2. Fallback: any markdown table row whose first cell looks like a ticker.

Output is a CSV file with the run metadata folded in as leading columns:
``RunDate,DataCollectedThrough,PredictionDate,Ticker,Decision``. Downstream
evaluation scripts read it with ``csv.DictReader``.
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
CSV_FIELDS = ["RunDate", "DataCollectedThrough", "PredictionDate", "Ticker", "Decision"]

# Fenced block: ```csv\nTicker,...\n...\n```  (the ```csv tag is optional)
_CSV_BLOCK_RE = re.compile(
    r"```(?:csv)?\s*\n(Ticker.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)
_TICKER_RE = re.compile(r"^[A-Za-z][A-Za-z.\-]{0,5}$")


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

    decisions = extract_decisions(p.read_text())

    run_date = current_date or ""
    data_through = market_data_date or ""
    pred_date = prediction_date or ""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for ticker, decision in decisions:
            writer.writerow(
                {
                    "RunDate": run_date,
                    "DataCollectedThrough": data_through,
                    "PredictionDate": pred_date,
                    "Ticker": ticker,
                    "Decision": decision,
                }
            )
    return decisions


if __name__ == "__main__":
    extracted = write_decision_table()
    print(f"Wrote {len(extracted)} decision(s) to {OUTPUT_TABLE}")
