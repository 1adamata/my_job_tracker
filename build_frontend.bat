@echo off
setlocal EnableExtensions
where node >nul 2>nul
if errorlevel 1 (
  echo ERROR: Node.js was not found.
  echo Install Node.js LTS from https://nodejs.org and reopen this window.
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: npm was not found. Reinstall Node.js LTS with npm enabled.
  exit /b 1
)

echo Node:
node --version
echo npm:
call npm --version

pushd "%~dp0frontend"
if not exist "node_modules\react\package.json" (
  echo Installing React dependencies. This requires internet on the first run...
  call npm install
  if errorlevel 1 (
    popd
    exit /b 1
  )
)

call npm run build
if errorlevel 1 (
  popd
  exit /b 1
)
popd
endlocal
