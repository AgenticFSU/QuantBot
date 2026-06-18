"""Nightly QuantBot pipeline: score yesterday's picks, then run a fresh crew.

Intended schedule: 9:00 PM US/Eastern on each trading day (Mon–Fri, excluding
market holidays). At that time today's session is closed, so we can:

1. Evaluate decisions made on the previous trading evening against today's move.
2. Run a new crew pass for the next trading day.

Use ``scripts/install_schedule.sh`` to install the macOS launchd job, or run
this script manually / from cron.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")

from sp_stock_agent.market_calendar import (  # noqa: E402
    is_trading_day,
    now_eastern,
    previous_trading_day,
)


def _python() -> Path:
    venv_python = _PROJECT_ROOT / ".venv" / "bin" / "python"
    if not venv_python.is_file():
        raise FileNotFoundError(
            f"Project venv not found at {venv_python}. "
            "Create it with: python3 -m venv .venv && .venv/bin/pip install -e ."
        )
    return venv_python


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--tickers-file",
        default="scripts/tickers_input.csv",
        help="Ticker CSV passed to sp_stock_agent.main (default: scripts/tickers_input.csv).",
    )
    ap.add_argument(
        "--skip-evaluation",
        action="store_true",
        help="Skip scoring the prior evening's decision table.",
    )
    ap.add_argument(
        "--skip-crew",
        action="store_true",
        help="Only run evaluation (useful for backfills).",
    )
    args = ap.parse_args(argv)

    today = now_eastern().date()
    if not is_trading_day(today):
        print(f"Skip: {today} is not a US trading day.")
        return 0

    python = _python()
    tickers_path = Path(args.tickers_file)
    if not tickers_path.is_file():
        print(f"Tickers file not found: {tickers_path}", file=sys.stderr)
        return 1

    if not args.skip_evaluation:
        pred_date = previous_trading_day(today).isoformat()
        print(f"=== Evaluation (prediction-date={pred_date}) ===")
        eval_cmd = [
            str(python),
            str(_PROJECT_ROOT / "scripts" / "evaluation_predictions.py"),
            "--prediction-date",
            pred_date,
        ]
        result = subprocess.run(eval_cmd, cwd=str(_PROJECT_ROOT))
        if result.returncode != 0:
            print(
                f"Evaluation exited {result.returncode} "
                "(no prior run or data not ready — continuing to crew)."
            )

    if args.skip_crew:
        return 0

    print("=== Crew run ===")
    crew_cmd = [
        str(python),
        "-m",
        "sp_stock_agent.main",
        "--tickers-file",
        str(tickers_path),
    ]
    return subprocess.run(crew_cmd, cwd=str(_PROJECT_ROOT)).returncode


if __name__ == "__main__":
    raise SystemExit(main())
