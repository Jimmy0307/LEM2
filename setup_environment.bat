@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

set "MODE=%~1"
if "%MODE%"=="" set "MODE=full"
if /I not "%MODE%"=="core" if /I not "%MODE%"=="full" (
    echo Usage: setup_environment.bat [core^|full]
    exit /b 2
)

echo ================================================================
echo  RoughSet Environment Setup - %MODE%
echo  Canonical runtime: Python 3.11-3.13
echo ================================================================

set "PYEXE=%CD%\.venv\Scripts\python.exe"

rem Existing virtual environments are disposable. Rebuild them if they were
rem created by an unsupported interpreter such as Python 3.14.
if exist "%PYEXE%" (
    "%PYEXE%" -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
    if not errorlevel 1 goto :install
    echo Existing .venv uses an unsupported Python runtime.
    echo Rebuilding .venv with Python 3.11-3.13...
    rmdir /s /q ".venv"
)

rem Prefer an explicitly bundled portable runtime when it is compatible.
if exist "%CD%\runtime\python.exe" (
    "%CD%\runtime\python.exe" -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
    if errorlevel 1 goto :portable_version_error
    echo Creating .venv with portable runtime...
    "%CD%\runtime\python.exe" -m venv ".venv"
    set "RC=!ERRORLEVEL!"
    if not "!RC!"=="0" goto :venv_error
    goto :install
)

rem The Python launcher may have multiple versions installed. Select a
rem compatible minor explicitly instead of using `py -3`, which chooses the
rem newest Python and selected Python 3.14 on the reported failing machine.
where py >nul 2>&1
if not errorlevel 1 (
    py -3.13 -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 (
        echo Creating .venv with Python 3.13...
        py -3.13 -m venv ".venv"
        if errorlevel 1 goto :venv_error
        goto :install
    )
    py -3.12 -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 (
        echo Creating .venv with Python 3.12...
        py -3.12 -m venv ".venv"
        if errorlevel 1 goto :venv_error
        goto :install
    )
    py -3.11 -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 (
        echo Creating .venv with Python 3.11...
        py -3.11 -m venv ".venv"
        if errorlevel 1 goto :venv_error
        goto :install
    )
)

rem A plain `python` command is acceptable only after checking its version.
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
    if not errorlevel 1 (
        echo Creating .venv with compatible python command...
        python -m venv ".venv"
        if errorlevel 1 goto :venv_error
        goto :install
    )
)

goto :compatible_python_not_found

:install
if not exist "%PYEXE%" goto :venv_error
"%PYEXE%" -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
if errorlevel 1 goto :python_version_error
"%PYEXE%" -m pip --version >nul 2>&1
if errorlevel 1 "%PYEXE%" -m ensurepip --upgrade >nul 2>&1
"%PYEXE%" -m pip --version >nul 2>&1
if errorlevel 1 goto :pip_error

rem Pip upgrade is best-effort only when no local offline wheelhouse is being used.
if not exist "%CD%\wheels\*.whl" "%PYEXE%" -m pip install --upgrade pip >nul 2>&1

set "REQFILE=requirements-lock.txt"
if /I "%MODE%"=="core" set "REQFILE=requirements-core.txt"

if exist "%CD%\wheels\*.whl" (
    echo Installing locked dependencies from local wheels ...
    "%PYEXE%" -m pip install --only-binary=:all: --no-index --find-links "%CD%\wheels" -r "%REQFILE%"
) else (
    echo Installing locked dependencies from package index...
    rem --only-binary prevents pip from silently compiling pandas/numpy from source.
    "%PYEXE%" -m pip install --only-binary=:all: -r "%REQFILE%"
)
if errorlevel 1 goto :pip_error

"%PYEXE%" -m roughset.environment --config "config.json"
if errorlevel 1 (
    echo NOTE: Base environment is installed. Optional adapters required by
    echo current real_data/config may still be installed automatically by run.bat.
)

echo.
echo ENVIRONMENT READY
exit /b 0

:compatible_python_not_found
echo.
echo ERROR: No compatible Python runtime was found.
echo This research lock requires Python 3.11-3.13.
echo Your installed Python 3.14 cannot use the pinned pandas==2.2.3 wheel.
echo.
echo Recommended fix:
echo   1. Double-click install_python_313.bat, or install Python 3.13 x64 manually.
echo   2. Run run.bat again.
echo.
echo Installed Python versions reported by the launcher:
where py >nul 2>&1 && py -0p
pause
exit /b 4

:portable_version_error
echo ERROR: runtime\python.exe is not Python 3.11-3.13.
echo Replace it with a compatible portable/runtime Python.
pause
exit /b 4

:python_version_error
echo ERROR: The created .venv is not using Python 3.11-3.13.
echo Delete .venv and rerun setup_environment.bat after installing Python 3.13.
pause
exit /b 4

:venv_error
echo ERROR: Failed to create .venv.
echo The selected Python runtime must support the venv module.
pause
exit /b 1

:pip_error
echo ERROR: Dependency installation failed.
echo The installer intentionally refuses source builds for locked binary packages.
echo Check Internet/proxy access and verify that Python 3.11-3.13 is being used.
pause
exit /b 1
