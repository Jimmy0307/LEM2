@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================================
echo  RoughSet Research Software - ALL POLICIES
echo ================================================================

set "PYEXE=%CD%\.venv\Scripts\python.exe"

echo [1/5] Checking core Python environment...
set "NEED_SETUP=0"
if not exist "%PYEXE%" set "NEED_SETUP=1"
if exist "%PYEXE%" (
    "%PYEXE%" -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
    if errorlevel 1 set "NEED_SETUP=1"
)
if "!NEED_SETUP!"=="1" (
    call "setup_environment.bat" core
    set "RC=!ERRORLEVEL!"
    if not "!RC!"=="0" exit /b !RC!
)

echo [2/5] Resolving dependencies required by current data/config...
"%PYEXE%" -m roughset.environment --config "config.json" --ensure
set "RC=!ERRORLEVEL!"
if not "!RC!"=="0" (
    echo ERROR: Could not prepare dependencies required by the current inputs.
    pause
    exit /b !RC!
)

echo [3/5] Verifying environment...
call "check_environment.bat"
set "RC=!ERRORLEVEL!"
if not "!RC!"=="0" (
    pause
    exit /b !RC!
)

echo [4/5] Running all configured prediction policies...
"%PYEXE%" "main.py" --config "config.json" --all-policies
set "RUN_EXIT=!ERRORLEVEL!"
if not "!RUN_EXIT!"=="0" (
    echo.
    echo RoughSet run failed with exit code !RUN_EXIT!.
    echo Check the ERROR message above, config.json, schema files, and real_data.
    pause
    exit /b !RUN_EXIT!
)

echo [5/5] Finished. Combined results are under outputs\batch_runs.
pause
exit /b 0
