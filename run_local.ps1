# Windows PowerShell Startup Script
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Starting Industrial Equipment Monitoring Backend Service" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check if .venv exists
if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    .\.venv\Scripts\pip.exe install -r requirements.txt
}

Write-Host "Running database seeding..." -ForegroundColor Green
.\.venv\Scripts\python.exe scripts\seed_database.py

Write-Host "Starting Uvicorn server on http://localhost:8000..." -ForegroundColor Green
Write-Host "OpenAPI documentation available at: http://localhost:8000/docs" -ForegroundColor Yellow
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
