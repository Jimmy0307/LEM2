@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================================
echo  Install Python 3.13 x64 for RoughSet canonical environment
echo ================================================================
echo.
echo This helper uses Windows Package Manager (winget).
echo It does NOT remove Python 3.14; both versions may coexist.
echo.

where winget >nul 2>&1
if errorlevel 1 (
    echo ERROR: winget was not found.
    echo Install Python 3.13 x64 manually from python.org, then rerun run.bat.
    pause
    exit /b 1
)

winget install -e --id Python.Python.3.13 --architecture x64 --accept-package-agreements --accept-source-agreements
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo.
    echo ERROR: Python 3.13 installation did not complete successfully.
    pause
    exit /b %RC%
)

echo.
echo Python 3.13 installation completed.
echo You can keep Python 3.14 installed. RoughSet will explicitly select 3.13.
echo Now run run.bat again.
pause
exit /b 0
