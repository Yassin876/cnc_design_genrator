# CAD Studio - Run All Services using System Python
# Run from: d:\download\cnc_design_genrator

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$PY = "python"

# 1. Main Backend (Port 8000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    cd '$ROOT\services\main_backend';
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
" -WindowStyle Normal

Start-Sleep -Seconds 2

# 2. 2D AI Server (Port 8001)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    cd '$ROOT\services\ai_server_2d';
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
" -WindowStyle Normal

Start-Sleep -Seconds 2

# 3. Edit Server (Port 8002)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    cd '$ROOT\services\edit_server';
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
" -WindowStyle Normal

Start-Sleep -Seconds 2

# 4. Nesting Worker (Port 8003)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    cd '$ROOT\services\nesting_worker';
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
" -WindowStyle Normal

Write-Host ""
Write-Host "All services started!" -ForegroundColor Green
Write-Host "  Main Backend   -> http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  2D AI Server   -> http://localhost:8001/health" -ForegroundColor Cyan
Write-Host "  Edit Server    -> http://localhost:8002/health" -ForegroundColor Cyan
Write-Host "  Nesting Worker -> http://localhost:8003/health" -ForegroundColor Cyan
