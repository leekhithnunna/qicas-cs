#!/usr/bin/env bash
# macOS / Linux: run tests, the CLI demo, and regenerate figures.   bash scripts/run_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || { echo "No .venv found. Run scripts/setup.sh first." >&2; exit 1; }
"$PY" -m pytest -q
"$PY" -m demo.run_demo
"$PY" -m demo.make_figures
