"""Capture reproducibility metadata for a QuantBot run.

:func:`capture_metadata` records the git revision, environment, model
configuration, and key package versions so an experiment can be reproduced and
cited in the paper. Output defaults to ``data/generated/evaluation_metadata.json``.
"""

import importlib.metadata as importlib_metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import yaml  # pyyaml is a transitive dependency of crewai
except Exception:  # pragma: no cover
    yaml = None

METADATA_FILE = os.getenv("EVAL_METADATA_FILE", "data/generated/evaluation_metadata.json")
AGENTS_CONFIG = str(Path(__file__).resolve().parent / "config" / "agents.yaml")

# Packages whose versions matter for reproducing results.
KEY_PACKAGES = [
    "crewai",
    "crewai-tools",
    "openai",
    "transformers",
    "torch",
    "langchain-community",
    "sec-parser",
    "html-to-markdown",
    "pydantic",
    "numpy",
]


def _git(*args: str) -> Optional[str]:
    try:
        return (
            subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return None


def _pkg_version(name: str) -> Optional[str]:
    try:
        return importlib_metadata.version(name)
    except Exception:
        return None


def _agent_models() -> dict:
    """Read each agent's configured LLM from agents.yaml."""
    p = Path(AGENTS_CONFIG)
    if not p.exists() or yaml is None:
        return {}
    try:
        cfg = yaml.safe_load(p.read_text()) or {}
        return {
            name: spec.get("llm")
            for name, spec in cfg.items()
            if isinstance(spec, dict) and "llm" in spec
        }
    except Exception:
        return {}


def capture_metadata(
    *,
    tickers: Optional[list] = None,
    current_date: Optional[str] = None,
    manager_model: Optional[str] = None,
    extra: Optional[dict] = None,
    path: str = METADATA_FILE,
) -> dict:
    """Capture and persist reproducibility metadata for a run."""
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git": {
            "commit": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(_git("status", "--porcelain")),
        },
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "tickers": tickers or [],
        "current_date": current_date,
        "manager_model": manager_model,
        "agent_models": _agent_models(),
        "package_versions": {name: _pkg_version(name) for name in KEY_PACKAGES},
    }
    if extra:
        metadata["extra"] = extra

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    print(json.dumps(capture_metadata(tickers=["AAPL"], current_date="2026-06-15"), indent=2))
