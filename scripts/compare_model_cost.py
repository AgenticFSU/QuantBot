"""Compare QuantBot run costs across model configurations.

Reads the run-cost ledger written by ``sp_stock_agent.usage_tracker``
(``data/generated/run_cost.json`` by default) and aggregates cost/latency/token
usage per model. Useful for selecting the best cost/latency model combination
and for the ablation study in the paper.

Usage:
    python scripts/compare_model_cost.py
    python scripts/compare_model_cost.py --run-cost data/generated/run_cost.json --csv out.csv
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

DEFAULT_RUN_COST = "data/generated/run_cost.json"


def load_runs(path: str) -> list:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Run-cost ledger not found: {path}. Run the crew first so "
            f"usage_tracker can create it."
        )
    data = json.loads(p.read_text())
    return data if isinstance(data, list) else [data]


def _avg(values: list):
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(mean(vals), 4) if vals else None


def _total(values: list):
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals), 4) if vals else None


def aggregate(runs: list) -> list:
    """Group runs by model and compute per-model summary statistics."""
    groups = defaultdict(list)
    for r in runs:
        groups[r.get("model", "unknown")].append(r)

    rows = []
    for model, items in sorted(groups.items()):
        rows.append(
            {
                "model": model,
                "runs": len(items),
                "avg_total_tokens": _avg([i.get("total_tokens") for i in items]),
                "avg_prompt_tokens": _avg([i.get("prompt_tokens") for i in items]),
                "avg_completion_tokens": _avg([i.get("completion_tokens") for i in items]),
                "avg_cost_usd": _avg([i.get("total_cost_usd") for i in items]),
                "total_cost_usd": _total([i.get("total_cost_usd") for i in items]),
                "avg_latency_sec": _avg([i.get("wall_clock_sec") for i in items]),
                "unpriced_runs": sum(1 for i in items if i.get("priced") is False),
            }
        )
    return rows


def print_table(rows: list) -> None:
    headers = [
        "model",
        "runs",
        "avg_total_tokens",
        "avg_cost_usd",
        "total_cost_usd",
        "avg_latency_sec",
        "unpriced_runs",
    ]
    widths = {h: max(len(h), *(len(str(r.get(h, ""))) for r in rows)) for h in headers} if rows else {}
    if not rows:
        print("No runs found.")
        return
    line = "  ".join(h.ljust(widths[h]) for h in headers)
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(r.get(h, "")).ljust(widths[h]) for h in headers))


def write_csv(rows: list, path: str) -> None:
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compare QuantBot run costs by model.")
    ap.add_argument("--run-cost", default=DEFAULT_RUN_COST, help="Path to run_cost.json")
    ap.add_argument("--csv", default=None, help="Optional path to write the summary as CSV")
    args = ap.parse_args(argv)

    try:
        runs = load_runs(args.run_cost)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    rows = aggregate(runs)
    print_table(rows)
    if any(r["unpriced_runs"] for r in rows):
        print(
            "\nNote: some runs are unpriced (model missing from model_pricing.json).",
            file=sys.stderr,
        )
    if args.csv:
        write_csv(rows, args.csv)
        print(f"\nWrote summary CSV to {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
