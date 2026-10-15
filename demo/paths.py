"""Project locations, computed from this file so every command works from any working directory.

Override with environment variables (see .env.example):
  QICAS_CONFIG   config YAML          (default: <root>/config/demo.yaml)
  QICAS_RESULTS  results directory    (default: <root>/results)
Relative values are resolved against the project root, not the current directory.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _env_path(var: str, default: Path) -> Path:
    value = os.environ.get(var, "").strip()
    if not value:
        return default
    p = Path(value).expanduser()
    return p if p.is_absolute() else ROOT / p


CONFIG = _env_path("QICAS_CONFIG", ROOT / "config" / "demo.yaml")
RESULTS = _env_path("QICAS_RESULTS", ROOT / "results")
RESULTS_JSON = RESULTS / "demo_run.json"
FIGURES = RESULTS / "figures"
