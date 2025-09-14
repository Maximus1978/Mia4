@echo off
setlocal ENABLEDELAYEDEXPANSION
REM User launch: minimal logs, user UI mode.
set MIA__UI_MODE=user
set MIA__LOG_LEVEL=INFO

if not exist .venv (echo [ERROR] Python venv not found. Please create .venv && exit /b 1)
call .venv\Scripts\activate.bat

start "MIA Backend" cmd /c "python -m mia4.api.app"

if exist chatgpt-design-app (pushd chatgpt-design-app & start "MIA UI" cmd /c "npm run dev" & popd) else (echo [WARN] chatgpt-design-app folder not found)

endlocal
