@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "PYEXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYEXE%" (
    echo ENVIRONMENT NOT READY: .venv not found.
    echo Run setup_environment.bat first.
    exit /b 3
)

"%PYEXE%" -m roughset.environment --config "config.json"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo.
    echo Environment check failed. Run setup_environment.bat full,
    echo or run run.bat and allow it to install only the adapters required by the current data.
)
exit /b %RC%
