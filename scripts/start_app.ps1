Set-Location (Join-Path $PSScriptRoot "..")

$venvActivate = Join-Path $PWD ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
} else {
    Write-Error "Virtual environment activation script not found at $venvActivate"
    exit 1
}

python app.py