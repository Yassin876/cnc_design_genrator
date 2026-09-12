# CAD Studio - Run All Microservices Locally
# Run this script from the root of the project: d:\download\cnc_design_genrator

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Main Backend (Port 8000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    cd '$ROOT\services\main_backend';
    Write-Host '🟢 Starting Main Backend on port 8000...' -ForegroundColor Green;
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
" -WindowStyle Normal

Start-Sleep -Seconds 2

# 2. 2D AI Server (Port 8001)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    cd '$ROOT\services\ai_server_2d';
    Write-Host '🟢 Starting 2D AI Server on port 8001...' -ForegroundColor Cyan;
    uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
" -WindowStyle Normal

Start-Sleep -Seconds 2

# 3. Edit Server (Port 8002)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    cd '$ROOT\services\edit_server';
    Write-Host '🟢 Starting Edit Server on port 8002...' -ForegroundColor Magenta;
    uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
" -WindowStyle Normal

Start-Sleep -Seconds 2

# 4. Nesting Worker (Port 8003)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    cd '$ROOT\services\nesting_worker';
    Write-Host '🟢 Starting Nesting Worker on port 8003...' -ForegroundColor Yellow;
    uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
" -WindowStyle Normal

Write-Host ""
Write-Host "All services are starting! Health check links:" -ForegroundColor Green
Write-Host "  Main Backend   -> http://localhost:8000/health"
Write-Host "  2D AI Server   -> http://localhost:8001/health"
Write-Host "  Edit Server    -> http://localhost:8002/health"
Write-Host "  Nesting Worker -> http://localhost:8003/health"
Write-Host ""
Write-Host "Swagger API Docs:" -ForegroundColor Cyan
Write-Host "  Main Backend   -> http://localhost:8000/docs"
