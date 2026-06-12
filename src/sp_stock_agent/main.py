#!/usr/bin/env python
import argparse
import csv
import json
import os
import sys
import time
import warnings
from collections.abc import Sequence
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from crewai.flow.flow import Flow, listen, start
from sp_stock_agent.crew import SpStockAgent
from .tools import Sec10KTool

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

_MAX_TICKERS = 15


def _read_tickers_from_csv(path: str) -> List[str]:
    """Load tickers from a single-column CSV.

    Each non-empty row must have exactly one non-empty cell (extra columns are an error).
    If there are two or more such rows, the first row is treated as a column header (any
    name, case-insensitive) and skipped; remaining rows are tickers.

    UTF-8 with optional BOM (``utf-8-sig``) for Excel exports. Empty rows skipped;
    cells starting with ``#`` after strip are skipped.
    """
    p = os.path.expanduser(path)
    with open(p, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.reader(f) if any((c or "").strip() for c in r)]
    if not rows:
        return []

    def _sole_cell(row: List[str]) -> str:
        stripped = [(c or "").strip() for c in row]
        non_empty = [c for c in stripped if c]
        if len(non_empty) > 1:
            raise ValueError(
                "CSV tickers file must have exactly one column (one non-empty cell per row). "
                f"Found {len(non_empty)} non-empty cells in a row: {non_empty!r}."
            )
        if len(non_empty) == 0:
            return ""
        return non_empty[0]

    # Normalize rows to single-cell strings; validates multi-column rows early.
    cells: List[str] = []
    for row in rows:
        s = _sole_cell(row)
        if not s or s.startswith("#"):
            continue
        cells.append(s.upper())

    if not cells:
        return []
    if len(cells) >= 2:
        return cells[1:]  # drop header (any label); rest are tickers
    return cells  # single row: no separate header row


def _read_tickers_file(path: str) -> List[str]:
    """Load tickers from a path.

    - ``.csv`` (case-insensitive): single-column CSV; optional header row (any name).
    - Otherwise: plain text, one symbol per line, UTF-8.

    Empty lines and lines whose first non-space character is ``#`` are ignored
    (plain-text mode only; CSV uses cell-based rules).
    """
    p = os.path.expanduser(path)
    if p.lower().endswith(".csv"):
        return _read_tickers_from_csv(p)

    with open(p, encoding="utf-8") as f:
        lines = f.readlines()
    out: List[str] = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s.upper())
    return out


def _parse_cli_tickers(argv: List[str]) -> List[str]:
    """Parse ticker symbols from CLI arguments (see ``run`` / ``run_crew``)."""
    parser = argparse.ArgumentParser(
        prog="run_crew",
        description="Run the stock analysis flow for the given tickers.",
    )
    parser.add_argument(
        "-f",
        "--tickers-file",
        metavar="PATH",
        help=(
            "Tickers file: ``.txt`` one symbol per line, or single-column ``.csv`` "
            "(optional first-row header with any column name). "
            "Mutually exclusive with positional TICKER arguments."
        ),
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        metavar="TICKER",
        help=(
            "Ticker symbols. Required unless you pass --tickers-file with at least "
            "one non-comment, non-blank line."
        ),
    )
    args = parser.parse_args(argv)

    from_file: List[str] = []
    if args.tickers_file:
        fp = os.path.expanduser(args.tickers_file)
        if not os.path.isfile(fp):
            parser.error(f"Tickers file not found: {args.tickers_file}")
        try:
            from_file = _read_tickers_file(fp)
        except ValueError as e:
            parser.error(str(e))

    positional = [t.strip().upper() for t in args.tickers if t and str(t).strip()]

    if from_file and positional:
        parser.error("Use either --tickers-file or positional tickers, not both.")

    result = from_file if from_file else positional
    if not result:
        parser.error(
            "Provide at least one ticker: pass positional TICKER symbols and/or "
            "--tickers-file PATH (``.txt`` line-based or ``.csv``; at least one ticker)."
        )
    return result


# Define our flow state model
class StockAnalysisState(BaseModel):
    raw_tickers: List[str] = Field(default_factory=list, description="Raw tickers from CLI")
    validated_tickers: List[str] = Field(default_factory=list, description="Validated stock tickers")

class StockAnalysisFlow(Flow[StockAnalysisState]):
    """Flow for analyzing stock tickers using SP Stock Agent crew"""

    @start()
    def get_tickers(self):
        """
        Normalize tickers supplied via ``run()`` / CLI (positional or --tickers-file).
        """
        if not self.state.raw_tickers:
            raise ValueError(
                "No tickers in flow state; run via CLI with positional tickers or --tickers-file."
            )

        print(f"\n== Tickers from CLI (max {_MAX_TICKERS}). ==\n")

        tickers = [t.upper() for t in self.state.raw_tickers]
        if len(tickers) > _MAX_TICKERS:
            warnings.warn(
                f"You entered more than {_MAX_TICKERS} tickers. "
                f"Only the first {_MAX_TICKERS} will be used.",
                UserWarning,
            )
            tickers = tickers[:_MAX_TICKERS]

        self.state.raw_tickers = tickers
        print(f"Received tickers: {self.state.raw_tickers}")
        return self.state.raw_tickers

    @listen(get_tickers)
    def validate_tickers(self, raw_tickers):
        """Validate the tickers against the available tickers list"""
        print("Validating Tickers...")
        
        try:
            # Load available tickers
            with open("tickers.json", "r") as f:
                available_tickers = set(json.load(f))
            
            validated = []
            for ticker in raw_tickers:
                ticker_upper = ticker.upper()
                if ticker_upper in available_tickers:
                    validated.append(ticker_upper)
                    print(f"✓ {ticker_upper} is valid")
                else:
                    warnings.warn(f"Invalid ticker: {ticker_upper}. Ticker removed", UserWarning)

            if len(validated) == 0:
                given = ", ".join(str(t).upper() for t in raw_tickers) if raw_tickers else "(none)"
                raise ValueError(
                    "No tickers passed validation against tickers.json (none of the symbols are "
                    f"keys in that file). Symbols provided: {given}. "
                    "Fix typos or choose symbols present in tickers.json."
                )

            self.state.validated_tickers = validated
            print(f"Final tickers: {self.state.validated_tickers}")
            return self.state.validated_tickers
            
        except FileNotFoundError:
            warnings.warn("tickers.json file not found. Proceeding with provided tickers.", UserWarning)
            self.state.validated_tickers = [t.upper() for t in raw_tickers]
            return self.state.validated_tickers
    
    @listen(get_tickers)
    def get_10K_document(self, raw_tickers):
        """Prefetch 10-K HTML per ticker; missing filings must not abort the flow."""
        if not raw_tickers:
            return
        for ticker in raw_tickers:
            try:
                _ = Sec10KTool()._run(ticker)
            except Exception as e:
                warnings.warn(f"10-K prefetch skipped for {ticker}: {e}", UserWarning)

    @listen(validate_tickers)
    def run_crew_analysis(self, validated_tickers):
        """
        Run the crew analysis with the validated tickers.
        """
        print(f"Starting stock analysis for: {validated_tickers}")
        
        # Prepare inputs for the crew
        crew_inputs = {
            "tickers": validated_tickers,
            "current_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        try:
            # Run the crew with the validated tickers
            result = SpStockAgent().crew().kickoff(inputs=crew_inputs)
            print("Stock analysis completed successfully!")
            return result
            
        except Exception as e:
            raise Exception(f"An error occurred while running the crew: {e}")

def run(argv: Optional[Sequence[str]] = None) -> int:
    """Run the stock analysis flow.

    Tickers must come from CLI positional arguments and/or ``--tickers-file``.

    ``argv`` defaults to ``sys.argv[1:]`` so ``run(["AAPL", "MSFT"])`` works from tests.

    Returns 0 on success, 1 on validation errors (e.g. no symbols match ``tickers.json``).
    Other exceptions propagate. Console entry points use ``sys.exit(run())``.
    """
    if argv is None:
        argv = sys.argv[1:]
    initial = _parse_cli_tickers(list(argv))
    if len(initial) > _MAX_TICKERS:
        warnings.warn(
            f"More than {_MAX_TICKERS} tickers supplied; using the first {_MAX_TICKERS}.",
            UserWarning,
        )
        initial = initial[:_MAX_TICKERS]

    print("Starting Stock Analysis Flow...")
    flow = StockAnalysisFlow()
    t0 = time.perf_counter()
    try:
        flow.kickoff(inputs={"raw_tickers": initial})
        print("\n=== Stock Analysis Flow Complete ===")
        return 0
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    finally:
        elapsed = time.perf_counter() - t0
        m, s = divmod(elapsed, 60.0)
        print(
            f"\n===== Wall-clock execution time: {elapsed:.2f}s "
            f"({int(m)}m {s:.1f}s) ====="
        )

def plot():
    """Generate a visualization of the flow"""
    flow = StockAnalysisFlow()
    flow.plot("stock_analysis_flow")
    print("Flow visualization saved to stock_analysis_flow.html")

def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "Quantum Computing Companies Profitability",
        'current_year': str(datetime.now().year)
    }
    try:
        SpStockAgent().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay(task_id):
    """
    Replay the crew execution from a specific task.
    """
    try:
        SpStockAgent().crew().replay(task_id=task_id)
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "Quantum Computing Companies Profitability",
        "current_year": str(datetime.now().year)
    }
    
    try:
        SpStockAgent().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

if __name__ == "__main__":
    raise SystemExit(run())
