@echo off
cd /d "%~dp0"
title Housing Data Cleaner - Process 2
set "HOUSING_CLEANER_PORT=8766"
set "BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED_PY%" goto bundled
where py >nul 2>nul
if not errorlevel 1 goto launcher
where python >nul 2>nul
if not errorlevel 1 goto system
echo Python 3.10 or later was not found.
pause
exit /b 1
:bundled
"%BUNDLED_PY%" server.py
goto done
:launcher
py -3 server.py
goto done
:system
python server.py
:done
if errorlevel 1 pause
