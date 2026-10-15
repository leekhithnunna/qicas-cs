# Windows: launch the Streamlit dashboard at http://localhost:8501 (Ctrl+C to stop).
#   powershell -ExecutionPolicy Bypass -File scripts\run_dashboard.ps1
# Extra arguments are passed to streamlit, e.g.  -- --server.port 8502
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$py = '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw 'No .venv found. Run scripts\setup.ps1 first.' }
& $py -m streamlit run app\dashboard.py @args
