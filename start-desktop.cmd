@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Python virtual environment is missing.
  echo Create it with a working Python installation, then install requirements.txt.
  pause
  exit /b 1
)

call npm.cmd run dev
