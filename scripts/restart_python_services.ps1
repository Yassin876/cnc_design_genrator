# Restart local Python microservices used by CNC Studio (ports 8000-8003).
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Stop-UvicornOnPort {
    param([int]$Port)
    $pids = @()
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        if ($connection.OwningProcess) { $pids += $connection.OwningProcess }
    }
    netstat -ano | ForEach-Object {
        if ($_ -match "127\.0\.0\.1:$Port\s+.*LISTENING\s+(\d+)") {
            $pids += [int]$Matches[1]
        }
    }
    $pids = $pids | Select-Object -Unique
    foreach ($procId in $pids) {
        Write-Host "Stopping process on port $Port (PID $procId)"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        & taskkill.exe /F /PID $procId 2>$null | Out-Null
    }
}

foreach ($port in 8000, 8001, 8002, 8003) {
    Stop-UvicornOnPort -Port $port
}

Start-Sleep -Seconds 1

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$logDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Start-UvicornService {
    param(
        [string]$Name,
        [string]$WorkDir,
        [string]$ModulePath,
        [int]$Port
    )
    $outLog = Join-Path $logDir "$Name.out.log"
    $errLog = Join-Path $logDir "$Name.err.log"
    Start-Process -WindowStyle Hidden -WorkingDirectory $WorkDir -FilePath $python -ArgumentList @(
        "-m", "uvicorn", $ModulePath, "--host", "127.0.0.1", "--port", "$Port"
    ) -RedirectStandardOutput $outLog -RedirectStandardError $errLog | Out-Null
}

Write-Host "Starting main backend on :8000"
Start-UvicornService -Name "main_backend" -WorkDir $ProjectRoot -ModulePath "backend.app.main:app" -Port 8000

Write-Host "Starting ai_server_2d on :8001"
Start-UvicornService -Name "ai_server_2d" -WorkDir (Join-Path $ProjectRoot "ai_server_2d") -ModulePath "app.main:app" -Port 8001

Write-Host "Starting edit_server on :8002"
Start-UvicornService -Name "edit_server" -WorkDir (Join-Path $ProjectRoot "core\edit_server") -ModulePath "app.main:app" -Port 8002

Write-Host "Starting nesting_worker on :8003"
Start-UvicornService -Name "nesting_worker" -WorkDir (Join-Path $ProjectRoot "core\nesting_worker") -ModulePath "app.main:app" -Port 8003

Write-Host "Waiting for health checks..."
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $backend = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 2
        $ai2d = Invoke-RestMethod "http://127.0.0.1:8001/health" -TimeoutSec 2
        if ($backend.api_revision -eq "2d-contract-v2" -and $ai2d.api_revision -eq "2d-contract-v2") {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 700
    }
}

if ($ready) {
    Write-Host "Services are healthy (2d-contract-v2)."
} else {
    Write-Warning "Services started, but health checks did not confirm 2d-contract-v2 yet."
}
