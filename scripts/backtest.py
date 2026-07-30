"""Performance backtest over QuantBot's logged predictions.

This is a *leakage-free* backtest: it never re-runs the agents and never fetches
new market data. It reads the decisions QuantBot already made (and that
``scripts/evaluation_predictions.py`` already scored against the next trading
day's intraday move) from ``scripts/evaluation_results.csv`` and reports how a
simple strategy built on those decisions would have performed.

Strategy modeled
----------------
Each ``TargetDate`` is one trading period. We take every ticker the bot tagged
"Invest" that day, weight them equally, and capture that day's intraday move
(open -> close). Days with no "Invest" call sit in cash (0% return).

Benchmark
---------
"Buy-everything": equal-weight ALL scored tickers each day regardless of the
bot's decision. This needs no extra API call (returns are already in the CSV)
and answers "did the bot's selectivity beat indiscriminately buying the same
universe?".

Run
---
    python scripts/backtest.py
    python scripts/backtest.py --results scripts/evaluation_results.csv \
        --report data/generated/backtest_report.md
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = "scripts/evaluation_results.csv"
DEFAULT_REPORT = "data/generated/backtest_report.md"

TRADING_DAYS_PER_YEAR = 252


def _is_invest(decision: str) -> bool:
    return decision.strip().lower() in ("invest", "buy", "yes")


def load_rows(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def group_by_target_date(rows: list[dict]) -> dict[str, list[dict]]:
    """Bucket scored rows by the day whose intraday move they were scored on."""
    by_date: dict[str, list[dict]] = {}
    for r in rows:
        target = (r.get("TargetDate") or "").strip()
        ret = _to_float(r.get("IntradayReturnPct"))
        if not target or ret is None:
            continue
        by_date.setdefault(target, []).append(r)
    return dict(sorted(by_date.items(), key=lambda kv: kv[0]))


def daily_returns(by_date: dict[str, list[dict]]) -> tuple[list[str], list[float], list[float]]:
    """Return (dates, strategy_daily_fraction, benchmark_daily_fraction)."""
    dates: list[str] = []
    strat: list[float] = []
    bench: list[float] = []
    for target, day_rows in by_date.items():
        all_rets = [_to_float(r["IntradayReturnPct"]) / 100.0 for r in day_rows]
        invest_rets = [
            _to_float(r["IntradayReturnPct"]) / 100.0
            for r in day_rows
            if _is_invest(r.get("Decision", ""))
        ]
        dates.append(target)
        strat.append(statistics.fmean(invest_rets) if invest_rets else 0.0)
        bench.append(statistics.fmean(all_rets) if all_rets else 0.0)
    return dates, strat, bench


def equity_curve(daily: list[float]) -> list[float]:
    equity = 1.0
    curve = []
    for r in daily:
        equity *= (1.0 + r)
        curve.append(equity)
    return curve


def max_drawdown(curve: list[float]) -> float:
    """Largest peak-to-trough decline as a positive fraction (0.20 = 20%)."""
    peak = -math.inf
    mdd = 0.0
    for v in curve:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, (peak - v) / peak)
    return mdd


def sharpe(daily: list[float]) -> float | None:
    """Annualized Sharpe (risk-free = 0). None if undefined."""
    if len(daily) < 2:
        return None
    sd = statistics.pstdev(daily)
    if sd == 0:
        return None
    return statistics.fmean(daily) / sd * math.sqrt(TRADING_DAYS_PER_YEAR)


def summarize(rows: list[dict]) -> dict:
    by_date = group_by_target_date(rows)
    dates, strat, bench = daily_returns(by_date)

    strat_curve = equity_curve(strat)
    bench_curve = equity_curve(bench)

    invest_rows = [r for r in rows if _is_invest(r.get("Decision", ""))]
    correct_invest = sum(
        1 for r in invest_rows if (_to_float(r.get("IntradayReturnPct")) or 0) > 0
    )
    scored = [r for r in rows if _to_float(r.get("IntradayReturnPct")) is not None]
    overall_correct = sum(
        1
        for r in scored
        if str(r.get("Correct", "")).strip().lower() in ("true", "1", "yes")
    )

    invest_pcts = [_to_float(r["IntradayReturnPct"]) for r in invest_rows]
    wins = [p for p in invest_pcts if p is not None and p > 0]
    losses = [p for p in invest_pcts if p is not None and p <= 0]

    return {
        "n_scored": len(scored),
        "n_days": len(dates),
        "date_range": (dates[0], dates[-1]) if dates else (None, None),
        "n_invest": len(invest_rows),
        "invest_hit_rate": (correct_invest / len(invest_rows)) if invest_rows else None,
        "overall_accuracy": (overall_correct / len(scored)) if scored else None,
        "strategy_total_return": (strat_curve[-1] - 1.0) if strat_curve else 0.0,
        "benchmark_total_return": (bench_curve[-1] - 1.0) if bench_curve else 0.0,
        "strategy_sharpe": sharpe(strat),
        "benchmark_sharpe": sharpe(bench),
        "strategy_max_drawdown": max_drawdown(strat_curve) if strat_curve else 0.0,
        "benchmark_max_drawdown": max_drawdown(bench_curve) if bench_curve else 0.0,
        "avg_win_pct": statistics.fmean(wins) if wins else None,
        "avg_loss_pct": statistics.fmean(losses) if losses else None,
        "best_day": max(zip(strat, dates), default=(None, None)),
        "worst_day": min(zip(strat, dates), default=(None, None)),
        "_dates": dates,
        "_strat_curve": strat_curve,
        "_bench_curve": bench_curve,
    }


def _pct(x: float | None) -> str:
    return f"{x * 100:.2f}%" if x is not None else "n/a"


def _num(x: float | None) -> str:
    return f"{x:.2f}" if x is not None else "n/a"


def render_report(s: dict) -> str:
    lo, hi = s["date_range"]
    lines = [
        "# QuantBot Backtest Report",
        "",
        f"_Generated {datetime.now():%Y-%m-%d %H:%M}_",
        "",
        f"- Scored predictions: **{s['n_scored']}**",
        f"- Trading days covered: **{s['n_days']}** ({lo} → {hi})",
        f"- \"Invest\" calls: **{s['n_invest']}**",
        "",
        "## Accuracy",
        "",
        f"- Overall accuracy: **{_pct(s['overall_accuracy'])}**",
        f"- \"Invest\" hit rate (next-day up): **{_pct(s['invest_hit_rate'])}**",
        f"- Avg winning Invest day: **{_num(s['avg_win_pct'])}%**",
        f"- Avg losing Invest day: **{_num(s['avg_loss_pct'])}%**",
        "",
        "## Returns (equal-weight intraday, compounded)",
        "",
        "| Metric | Strategy (Invest calls) | Benchmark (buy everything) |",
        "|---|---|---|",
        f"| Total return | {_pct(s['strategy_total_return'])} | {_pct(s['benchmark_total_return'])} |",
        f"| Annualized Sharpe | {_num(s['strategy_sharpe'])} | {_num(s['benchmark_sharpe'])} |",
        f"| Max drawdown | {_pct(s['strategy_max_drawdown'])} | {_pct(s['benchmark_max_drawdown'])} |",
        "",
    ]
    best_r, best_d = s["best_day"]
    worst_r, worst_d = s["worst_day"]
    if best_d:
        lines += [
            f"- Best day: **{_pct(best_r)}** on {best_d}",
            f"- Worst day: **{_pct(worst_r)}** on {worst_d}",
            "",
        ]
    if s["_dates"]:
        lines += ["## Daily equity curve", "", "| Date | Strategy | Benchmark |", "|---|---|---|"]
        for d, sc, bc in zip(s["_dates"], s["_strat_curve"], s["_bench_curve"]):
            lines.append(f"| {d} | {sc:.4f} | {bc:.4f} |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default=DEFAULT_RESULTS, help="Scored predictions CSV.")
    ap.add_argument("--report", default=DEFAULT_REPORT, help="Markdown report output path.")
    args = ap.parse_args(argv)

    results_path = Path(args.results)
    if not results_path.is_absolute():
        results_path = _PROJECT_ROOT / results_path

    rows = load_rows(results_path)
    if not rows:
        print(
            f"No scored predictions found at {results_path}.\n"
            "Run the bot for several trading days and score each with\n"
            "  python scripts/evaluation_predictions.py --prediction-date YYYY-MM-DD\n"
            "then re-run this backtest."
        )
        return 0

    summary = summarize(rows)
    report = render_report(summary)

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = _PROJECT_ROOT / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)

    print(report)
    print(f"\nReport written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
