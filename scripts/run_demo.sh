#!/usr/bin/env bash
set -e
source .venv/bin/activate
python -m demo.run_demo
python -m demo.make_figures
streamlit run app/dashboard.py
