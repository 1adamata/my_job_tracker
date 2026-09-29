@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Job Command Center

echo ==================================================
echo   Job Command Center - startup
echo ==================================================
echo.

where py >nul 2>nul
if not errorlevel 1 (
  set "PY_CMD=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 goto :missing_python
  set "PY_CMD=python"
)

echo [1/5] Checking Python...
%PY_CMD% --version
if errorlevel 1 goto :failed

if not exist ".venv\Scripts\python.exe" (
  echo [2/5] Creating Python environment...
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto :failed
) else (
  echo [2/5] Python environment found.
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :failed

echo [3/5] Installing Python dependencies...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :python_dependencies_failed
python -m pip install --upgrade --only-binary=:all: -r requirements.txt
if errorlevel 1 goto :python_dependencies_failed

echo [4/5] Building React dashboard...
call build_frontend.bat
if errorlevel 1 goto :failed

echo [5/5] Starting http://127.0.0.1:8765
start "" http://127.0.0.1:8765
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
if errorlevel 1 goto :failed
goto :end

:missing_python
echo.
echo ERROR: Python was not found.
echo Install Python 3.11 or newer and enable "Add Python to PATH".
goto :failed

:python_dependencies_failed
echo.
echo ERROR: Python dependencies could not be installed.
echo This package requires wheels compatible with your Python version.
echo Confirm that the computer is online, then run this launcher again.
echo If this is an older extracted copy, download the updated package.
goto :failed

:failed
echo.
echo ==================================================
echo STARTUP FAILED. The useful error is directly above.
echo Take a screenshot of this entire window and send it to me.
echo ==================================================
pause
exit /b 1

:end
endlocal
