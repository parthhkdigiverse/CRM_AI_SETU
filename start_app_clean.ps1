# Clean startup script for CRM AI SETU
# Kills any existing process on port 8000 before starting the app

$port = 8000
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "CRM AI SETU - Clean Startup Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Try to kill any process using port 8000
$procs = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($procs) {
    Write-Host "Port $port is in use. Clearing..." -ForegroundColor Yellow
    foreach ($proc in $procs) {
        $process = Get-Process -Id $proc.OwningProcess -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Killing process: $($process.ProcessName) (PID: $($proc.OwningProcess))" -ForegroundColor Yellow
            Stop-Process -Id $proc.OwningProcess -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }
    }
}

Write-Host "Starting application..." -ForegroundColor Green
Set-Location $scriptDir
& ".venv\Scripts\python.exe" "app.py"
