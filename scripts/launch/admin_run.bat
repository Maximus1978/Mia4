@echo off
setlocal ENABLEDELAYEDEXPANSION
echo [TRACE] enter: admin_run.bat
cd /d "%~dp0..\.." || (echo [ERROR] cd to repo root failed & goto END_ADMIN)
echo [TRACE] cwd=%CD%
REM Admin launch: enables verbose logging, admin UI mode, debug features.
set MIA_UI_MODE=admin
set MIA__logging__level=debug
set MIA__EVENTBUS_TRACE=0
if "%MIA_ADMIN_STAY%"=="" set MIA_ADMIN_STAY=1
echo [INFO] UI_MODE=%MIA_UI_MODE% LOG_LEVEL=%MIA__logging__level% STAY=%MIA_ADMIN_STAY%

if not exist .venv (
	echo [ERROR] Python venv not found. Create one:
	echo    python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
	goto END_ADMIN
)
call .venv\Scripts\activate.bat >nul 2>&1 || (echo [ERROR] venv activate failed & goto END_ADMIN)
if not exist .venv\Scripts\python.exe (echo [ERROR] Missing python in venv & goto END_ADMIN)
set PY_EXE=%CD%\.venv\Scripts\python.exe
if not exist "%PY_EXE%" (echo [ERROR] Expected venv python missing at %PY_EXE% & goto END_ADMIN)
echo [INFO] Python=%PY_EXE%
set PYTHONPATH=src
echo [INFO] PYTHONPATH=%PYTHONPATH%

REM --- Backend ---
echo [TRACE] backend: start
start "MIA Backend" cmd /k "set PYTHONPATH=%PYTHONPATH% && %PY_EXE% -m uvicorn mia4.api.app:app --host 127.0.0.1 --port 8000"

REM --- Frontend (dev server) ---
if exist chatgpt-design-app (
	pushd chatgpt-design-app
	where npm >nul 2>&1 || (echo [ERROR] npm not found in PATH. Install Node.js and re-run. & popd & goto AFTER_FRONT)
	if not exist node_modules (
		echo [INFO] Installing npm deps (first run)
		call npm install || (echo [ERROR] npm install failed & popd & goto AFTER_FRONT)
	) else (
		echo [INFO] node_modules present.
	)
	echo [TRACE] launching UI dev server (npm run start)
	start "MIA UI" cmd /k "npm run start -- --host --port 3000"
	popd
) else (
	echo [WARN] chatgpt-design-app folder not found (UI skipped)
)
:AFTER_FRONT
echo [HINT] Open http://localhost:3000/?dev=1  (dev panels)  |  Backend API: http://127.0.0.1:8000/health
echo [HINT] To disable auto-stay: set MIA_ADMIN_STAY=0
echo [HINT] To rebuild static UI via run_all:  set MIA_UI_FORCE_REBUILD=1 & scripts\launch\run_all.bat

:END_ADMIN
if "%MIA_ADMIN_STAY%"=="1" (
	echo.
	echo [INFO] Admin launcher finished. Press any key to close.
	pause >nul
)
echo [TRACE] end: admin_run.bat
endlocal
