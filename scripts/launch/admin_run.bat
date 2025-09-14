@echo off
setlocal ENABLEDELAYEDEXPANSION
REM Admin launch: enables verbose logging, admin UI mode, debug features.
set MIA__UI_MODE=admin
set MIA__LOG_LEVEL=DEBUG
set MIA__EVENTBUS_TRACE=0
REM Optional: preload model to reduce first-token latency.
REM You can set MIA__PRELOAD_PRIMARY=1 to force warm load (future flag placeholder).

if not exist .venv (echo [ERROR] Python venv not found. Please create .venv && exit /b 1)
call .venv\Scripts\activate.bat

REM Start backend API (assumes module mia4.api.app:main will exist)
start "MIA Backend" cmd /c "python -m mia4.api.app"

REM Start frontend (Vite dev server)
if exist chatgpt-design-app (pushd chatgpt-design-app & start "MIA UI" cmd /c "npm run dev" & popd) else (echo [WARN] chatgpt-design-app folder not found)

endlocal
