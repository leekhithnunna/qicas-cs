# Windows: run tests, the CLI demo, and regenerate figures.
#   powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$py = '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw 'No .venv found. Run scripts\setup.ps1 first.' }
foreach ($step in @(@('-m', 'pytest', '-q'), @('-m', 'demo.run_demo'), @('-m', 'demo.make_figures'))) {
    & $py @step
    if ($LASTEXITCODE -ne 0) { throw "failed: python $step" }
}
