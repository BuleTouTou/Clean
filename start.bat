@echo off
cd /d "%~dp0"
title Housing Data Cleaner
set "HOUSING_CLEANER_OPEN_BROWSER=1"
if not defined HOUSING_CLEANER_PORT set "HOUSING_CLEANER_PORT=8765"

where uv >nul 2>nul
if errorlevel 1 (
    echo uv was not found.
    echo Install uv: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo Frontend build output was not found.
    echo Run: cd frontend ^&^& bun install ^&^& bun run build
    pause
    exit /b 1
)

uv run uvicorn backend.app:app --host 127.0.0.1 --port %HOUSING_CLEANER_PORT%
if errorlevel 1 pause
