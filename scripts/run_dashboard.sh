#!/usr/bin/env bash
# macOS / Linux: launch the Streamlit dashboard at http://localhost:8501 (Ctrl+C to stop).
#   bash scripts/run_dashboard.sh [extra streamlit args, e.g. --server.port 8502]
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || { echo "No .venv found. Run scripts/setup.sh first." >&2; exit 1; }
exec "$PY" -m streamlit run app/dashboard.py "$@"
