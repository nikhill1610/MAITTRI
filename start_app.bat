@echo off
title MAITRI Smart Agriculture - Startup
echo ============================================================
echo   Starting MAITRI Smart Agriculture Platform
echo ============================================================
echo.

setlocal enabledelayedexpansion

:: Detect Python executable (root venv, backend venv, or system python)
if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
) else if exist "%~dp0backend\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0backend\venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [1/2] Launching FastAPI Backend on http://0.0.0.0:8000 (accessible on LAN) ...
start "MAITRI Backend" cmd /k "cd /d %~dp0backend && "!PYTHON_EXE!" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [2/2] Launching Vite Frontend on http://localhost:5173 ...
start "MAITRI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================================
echo   Both services are starting!
echo   Open your browser at: http://localhost:5173
echo ============================================================
pause
