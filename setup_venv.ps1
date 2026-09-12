# CAD Studio - Setup Virtual Environment with All Dependencies
# Run from: d:\download\cnc_design_genrator

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV = "$ROOT\.venv"

Write-Host "Creating virtual environment at $VENV ..." -ForegroundColor Cyan
python -m venv $VENV

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& "$VENV\Scripts\Activate.ps1"

Write-Host "Upgrading pip..." -ForegroundColor Yellow
& "$VENV\Scripts\python.exe" -m pip install --upgrade pip

Write-Host "Installing all service dependencies..." -ForegroundColor Cyan

& "$VENV\Scripts\pip.exe" install `
    fastapi `
    uvicorn `
    httpx `
    pydantic `
    python-dotenv `
    requests `
    google-genai `
    huggingface_hub `
    Pillow `
    python-jose `
    supabase `
    python-multipart `
    ezdxf `
    shapely `
    rectpack `
    gradio_client `
    numpy

Write-Host ""
Write-Host "All packages installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the venv manually, run:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "To run all services inside the venv, run:" -ForegroundColor Yellow
Write-Host "  .\run_all_venv.ps1"
