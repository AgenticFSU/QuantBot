"""Token and USD cost tracking for QuantBot crew runs.

After a crew run, :func:`record_run` appends one record (tokens, latency, and
USD cost) to ``data/generated/run_cost.json``. Those records are consumed by
``scripts/compare_model_cost.py`` to compare model configurations on
cost/latency for the ablation study.

Pricing is read from ``src/sp_stock_agent/config/model_pricing.json`` (USD per
1,000,000 tokens). EDIT that file with your exact provider rates; the built-in
``DEFAULT_PRICING`` values are placeholders and should be confirmed before any
numbers are reported.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Output ledger and pricing config (override locations via env if needed).
RUN_COST_FILE = os.getenv("RUN_COST_FILE", "data/generated/run_cost.json")
PRICING_FILE = os.getenv(
    "MODEL_PRICING_FILE",
    str(Path(__file__).resolve().parent / "config" / "model_pricing.json"),
)

# USD per 1,000,000 tokens. PLACEHOLDERS — confirm against your provider's rates.
# A JSON file at ``PRICING_FILE`` overrides/extends these entries.
DEFAULT_PRICING = {
    "openai/gpt-4.1": {"input_per_million": 2.0, "output_per_million": 8.0},
}


def _load_pricing() -> dict:
    """Merge the on-disk pricing file over the built-in defaults."""
    pricing = {k: dict(v) for k, v in DEFAULT_PRICING.items()}
    p = Path(PRICING_FILE)
    if p.exists():
        try:
            pricing.update(json.loads(p.read_text()))
        except Exception:
            pass
    return pricing


def _normalize_usage(token_usage: Any) -> dict:
    """Coerce a CrewAI ``UsageMetrics`` / dict / object into a plain dict."""
    if token_usage is None:
        return {}
    if hasattr(token_usage, "model_dump"):
        try:
            return token_usage.model_dump()
        except Exception:
            pass
    if isinstance(token_usage, dict):
        return token_usage
    keys = [
        "total_tokens",
        "prompt_tokens",
        "completion_tokens",
        "cached_prompt_tokens",
        "successful_requests",
    ]
    return {k: getattr(token_usage, k, None) for k in keys}


def _lookup_rates(model: str, pricing: dict) -> Optional[dict]:
    """Find pricing for ``model``, ignoring any provider prefix.

    CrewAI may report the model as ``gpt-4.1`` while pricing is keyed
    ``openai/gpt-4.1`` (or vice versa), so we match on the final path segment.
    """
    if model in pricing:
        return pricing[model]
    base = model.split("/")[-1]
    if base in pricing:
        return pricing[base]
    for key, rates in pricing.items():
        if key.split("/")[-1] == base:
            return rates
    return None


def compute_cost(
    model: str,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    pricing: Optional[dict] = None,
) -> dict:
    """Return input/output/total USD cost for the given token counts.

    If the model has no pricing entry, costs are ``None`` and ``priced`` is
    ``False`` so downstream tooling can flag unpriced runs instead of inventing
    numbers.
    """
    pricing = pricing or _load_pricing()
    rates = _lookup_rates(model, pricing)
    if not rates:
        return {
            "input_cost_usd": None,
            "output_cost_usd": None,
            "total_cost_usd": None,
            "priced": False,
        }
    in_cost = (prompt_tokens or 0) / 1_000_000 * rates["input_per_million"]
    out_cost = (completion_tokens or 0) / 1_000_000 * rates["output_per_million"]
    return {
        "input_cost_usd": round(in_cost, 6),
        "output_cost_usd": round(out_cost, 6),
        "total_cost_usd": round(in_cost + out_cost, 6),
        "priced": True,
    }


def record_run(
    *,
    model: str,
    token_usage: Any,
    tickers: Optional[list] = None,
    wall_clock_sec: Optional[float] = None,
    agent_models: Optional[dict] = None,
    run_id: Optional[str] = None,
    extra: Optional[dict] = None,
    path: str = RUN_COST_FILE,
) -> dict:
    """Compute cost for a run and append a record to the run-cost ledger."""
    usage = _normalize_usage(token_usage)
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    cost = compute_cost(model, prompt_tokens, completion_tokens)

    record = {
        "run_id": run_id or str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "agent_models": agent_models or {},
        "tickers": tickers or [],
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cached_prompt_tokens": usage.get("cached_prompt_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "successful_requests": usage.get("successful_requests"),
        "wall_clock_sec": round(wall_clock_sec, 2) if wall_clock_sec is not None else None,
        **cost,
    }
    if extra:
        record["extra"] = extra

    _append(path, record)
    return record


def _append(path: str, record: dict) -> None:
    """Append ``record`` to the JSON array at ``path`` (created if missing)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data: list = []
    if p.exists():
        try:
            loaded = json.loads(p.read_text())
            data = loaded if isinstance(loaded, list) else [loaded]
        except Exception:
            data = []
    data.append(record)
    p.write_text(json.dumps(data, indent=2))


if __name__ == "__main__":
    demo = record_run(
        model="openai/gpt-4.1",
        token_usage={"prompt_tokens": 12000, "completion_tokens": 3000, "total_tokens": 15000},
        tickers=["AAPL"],
        wall_clock_sec=120.0,
    )
    print(json.dumps(demo, indent=2))
