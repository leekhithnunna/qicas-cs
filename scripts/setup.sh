#!/usr/bin/env bash
# macOS / Linux setup: creates .venv with Python 3.12 (via uv) and installs requirements.
#   bash scripts/setup.sh
# Works from any directory. Needs any Python >= 3.10 to bootstrap uv;
# uv downloads a managed Python 3.12 if 3.12 is not installed.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
    if command -v uv >/dev/null 2>&1; then
        uv venv --python 3.12 --seed .venv
    else
        python3 -m pip install --user --quiet uv
        python3 -m uv venv --python 3.12 --seed .venv
    fi
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
echo "Setup complete. Next: bash scripts/run_dashboard.sh"
