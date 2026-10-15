# Windows setup: creates .venv with Python 3.12 (via uv) and installs requirements.
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
# Works from any directory. Needs any Python >= 3.10 on PATH to bootstrap uv;
# uv downloads a managed Python 3.12 if 3.12 is not installed.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

function Invoke-Checked { & $args[0] $args[1..($args.Count - 1)]; if ($LASTEXITCODE -ne 0) { throw "failed: $args" } }

$venvPy = '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) {
    $boot = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
    Invoke-Checked $boot -m pip install --user --quiet uv
    Invoke-Checked $boot -m uv venv --python 3.12 --seed .venv
}
Invoke-Checked $venvPy -m pip install --upgrade pip
Invoke-Checked $venvPy -m pip install -r requirements.txt
Invoke-Checked $venvPy -m pytest -q
Write-Host "Setup complete. Next: powershell -ExecutionPolicy Bypass -File scripts\run_dashboard.ps1"
