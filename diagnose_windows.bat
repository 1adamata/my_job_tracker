@echo off
setlocal
cd /d "%~dp0"
echo === Python launchers ===
where py 2>nul
py --version 2>nul
where python 2>nul
python --version 2>nul
echo.
echo === Node and npm ===
where node 2>nul
node --version 2>nul
where npm 2>nul
call npm --version 2>nul
echo.
echo === Ollama ===
where ollama 2>nul
ollama --version 2>nul
echo.
echo === Port 8765 ===
netstat -ano | findstr ":8765"
echo.
echo === Project files ===
if exist requirements.txt (echo requirements.txt OK) else (echo requirements.txt MISSING)
if exist frontend\package.json (echo frontend\package.json OK) else (echo frontend\package.json MISSING)
if exist app\main.py (echo app\main.py OK) else (echo app\main.py MISSING)
echo.
echo Send a screenshot of this window together with the run_windows.bat error.
pause
