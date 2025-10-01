@echo off
setlocal ENABLEDELAYEDEXPANSION
echo [TRACE] enter: run_all.bat
REM ===== MIA4 Unified Launcher =====
REM Usage: run_all.bat [user|admin]  (env MIA_LAUNCH_TEST=1 for headless probe mode)

cd /d "%~dp0..\.." || (echo [ERROR] cd repo root failed & goto LAUNCH_END_ERR)
echo [TRACE] cwd=%CD%
set MODE=%1
if "%MODE%"=="" set MODE=user
echo [TRACE] arg.MODE=%MODE%
echo [TRACE] flags: MIA_LAUNCH_SMOKE=%MIA_LAUNCH_SMOKE% MIA_LAUNCH_TEST=%MIA_LAUNCH_TEST%
REM Control whether backend runs in its own window (1) or background of this window (0)
if "%MIA_BACKEND_WINDOW%"=="" set MIA_BACKEND_WINDOW=1
REM UI mode now uses non-config env var MIA_UI_MODE to avoid config schema extra keys
if /I "%MODE%"=="admin" (
  set MIA_UI_MODE=admin
  set MIA__logging__level=debug
) else if /I "%MODE%"=="dev" (
  set MIA_UI_MODE=dev
  set MIA__logging__level=debug
  REM Force dev server usage for full dev features
  set MIA_UI_STATIC=0
  set MIA_DEV_AUTO=1
  REM Nudge GPU layers for heavy GGUF if not explicitly set
  if "%MIA__llm__primary__n_gpu_layers%"=="" set MIA__llm__primary__n_gpu_layers=20
) else (
  set MIA_UI_MODE=user
  set MIA__logging__level=info
)

set VENV_DIR=.venv
set VENV_PY=%VENV_DIR%\Scripts\python.exe
set VENV_PIP=%VENV_DIR%\Scripts\pip.exe
REM sanitize any accidental embedded quotes
set "VENV_PY=%VENV_PY:"=%"
if not exist %VENV_DIR% (
  echo [INFO] Creating venv
  python -m venv %VENV_DIR% >nul 2>&1
)
if not exist %VENV_PY% (
  echo [ERROR] Missing %VENV_PY%
  goto LAUNCH_END_ERR
)
rem Robust deps probe without complex || nesting (less parser pitfalls)
"%VENV_PIP%" show fastapi >nul 2>&1
if errorlevel 1 (
  echo [INFO] Installing backend deps
  "%VENV_PIP%" install -q -r requirements.txt || (echo [ERROR] pip failed & goto LAUNCH_END_ERR)
)
set ACTUAL_PY=%CD%\%VENV_PY%
echo [INFO] Python=%ACTUAL_PY% MODE=%MODE% UI_MODE=%MIA_UI_MODE% TEST=%MIA_LAUNCH_TEST%
set PYTHONPATH=src
echo [INFO] PYTHONPATH=%PYTHONPATH%
if "%MIA_LLAMA_FAKE%"=="" set MIA_LLAMA_FAKE=0
echo [INFO] MIA_LLAMA_FAKE=%MIA_LLAMA_FAKE%

set PYTHONUTF8=1
set PYTHONIOENCODING=UTF-8
set TMP_LAUNCH=.launch_tmp
if not exist %TMP_LAUNCH% mkdir %TMP_LAUNCH% >nul 2>&1

REM --- UI static prebuild (if requested) BEFORE backend start ---
echo [TRACE] prebuild-ui: begin (MIA_UI_STATIC=%MIA_UI_STATIC%)
REM Default to static build to ensure UI is served by backend on :8000
REM Default changed: prefer dev server for full dev features unless explicitly forced static.
REM To force static build: set MIA_UI_STATIC=1 before calling this script.
if "%MIA_UI_STATIC%"=="" set MIA_UI_STATIC=0
if "%MIA_UI_STATIC%"=="1" goto BUILD_STATIC
goto END_PREBUILD

:BUILD_STATIC
if not exist chatgpt-design-app (
  echo [WARN] UI folder missing (skip static build)
  goto END_PREBUILD
)
pushd chatgpt-design-app
for /f "delims=" %%H in ('git rev-parse --short=12 HEAD 2^>nul') do set GIT_HEAD=%%H
if exist dist\.build_commit set /p DIST_COMMIT=<dist\.build_commit
REM Staleness decision
set NEED_BUILD=1
if "%MIA_UI_FORCE_REBUILD%"=="1" (
  echo [INFO] MIA_UI_FORCE_REBUILD=1 (forcing rebuild)
) else (
  if defined GIT_HEAD if exist dist if exist dist\.build_commit if "%DIST_COMMIT%"=="%GIT_HEAD%" set NEED_BUILD=0
)
if "%NEED_BUILD%"=="0" (
  echo [INFO] UI dist up-to-date (commit %GIT_HEAD%).
  set UI_MODE_STATIC=1
  popd
  goto END_PREBUILD
)
if exist dist (
  echo [INFO] Cleaning stale dist (dist=%DIST_COMMIT% head=%GIT_HEAD%)
  rmdir /s /q dist >nul 2>&1
)
where npm >nul 2>&1 || (echo [ERROR] npm not found in PATH. Install Node.js and retry. & popd & goto END_PREBUILD)
if not exist node_modules (
  echo [INFO] Running npm install (first time)
  call npm install > ..\%TMP_LAUNCH%\npm-install.log 2>&1 || (echo [ERROR] npm install failed. See ..\%TMP_LAUNCH%\npm-install.log & popd & goto END_PREBUILD)
  echo [INFO] npm install completed.
) else (
  echo [INFO] node_modules present (skip install).
)
for /f "delims=" %%P in ('where npm') do set NPM_EXE=%%P
echo [INFO] Building static UI (pre-backend)
call "%NPM_EXE%" run build > ..\%TMP_LAUNCH%\ui-build.log 2>&1
if errorlevel 1 (
  echo [ERROR] UI build failed. See ..\%TMP_LAUNCH%\ui-build.log
  popd
  goto END_PREBUILD
)
if defined GIT_HEAD (echo %GIT_HEAD%> dist\.build_commit) else (echo unknown> dist\.build_commit)
echo [INFO] Static build complete (served by backend :8000)
set UI_MODE_STATIC=1
popd

:END_PREBUILD

:START_BACKEND
REM --- Start backend (non-blocking, supervise optional) ---
echo [TRACE] backend: start
set BACKEND_LOG=%TMP_LAUNCH%\backend.log
if "%MIA_BACKEND_STAY%"=="" set MIA_BACKEND_STAY=1
if "%MIA_BACKEND_STAY%"=="0" goto BACKEND_SINGLE
echo [INFO] Backend supervise loop enabled (MIA_BACKEND_STAY=%MIA_BACKEND_STAY%).
(
  echo @echo off
  echo set PYTHONPATH=%PYTHONPATH%
  echo :LOOP
  echo echo [BACKEND] starting ^>^> "%BACKEND_LOG%"
  echo call "%VENV_PY%" -m uvicorn mia4.api.app:app --host 127.0.0.1 --port 8000 --no-access-log ^>^> "%BACKEND_LOG%" 2^>^&1
  echo echo [BACKEND] exited %%errorlevel%% ^>^> "%BACKEND_LOG%"
  echo timeout /t 2 ^>nul
  echo goto LOOP
) > "%TMP_LAUNCH%\backend_loop.cmd"
REM Start backend loop; default in a separate window so it survives launcher exit
if "%MIA_BACKEND_WINDOW%"=="1" (
  start "MIA Backend" cmd /c "%TMP_LAUNCH%\backend_loop.cmd"
) else (
  start /b "" cmd /c "%TMP_LAUNCH%\backend_loop.cmd"
)
goto BACKEND_STARTED
:BACKEND_SINGLE
echo [INFO] Backend supervise disabled.
(
  echo @echo off
  echo set PYTHONPATH=%PYTHONPATH%
  echo echo [BACKEND] starting ^>^> "%BACKEND_LOG%"
  echo call "%VENV_PY%" -m uvicorn mia4.api.app:app --host 127.0.0.1 --port 8000 --no-access-log ^>^> "%BACKEND_LOG%" 2^>^&1
) > "%TMP_LAUNCH%\backend_once.cmd"
REM Start single backend; default in a separate window so it survives launcher exit
if "%MIA_BACKEND_WINDOW%"=="1" (
  start "MIA Backend" cmd /c "%TMP_LAUNCH%\backend_once.cmd"
) else (
  start /b "" cmd /c "%TMP_LAUNCH%\backend_once.cmd"
)
:BACKEND_STARTED

REM --- Wait health (5s) ---
echo [TRACE] health: wait
set /a TRY=0
REM If dev mode and possibly heavy model, extend wait window (up to ~60s)
set MAX_TRIES=20
if /I "%MODE%"=="dev" set MAX_TRIES=120
echo import urllib.request,sys> %TMP_LAUNCH%\_health.py
echo try:>> %TMP_LAUNCH%\_health.py
echo ^    urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1)>> %TMP_LAUNCH%\_health.py
echo ^    sys.exit(0)>> %TMP_LAUNCH%\_health.py
echo except Exception: sys.exit(1)>> %TMP_LAUNCH%\_health.py
:WAIT_HEALTH
echo [TRACE] health: try !TRY!/^%MAX_TRIES%
"%VENV_PY%" %TMP_LAUNCH%\_health.py >nul 2>&1 && goto HEALTH_OK
set /a TRY+=1
if %TRY% GEQ %MAX_TRIES% (
  echo [WARN] Health not confirmed; dumping backend log
  type %BACKEND_LOG%
  echo [DEBUG] Installed packages:
  "%VENV_PIP%" list ^| findstr /R /C:"fastapi" /C:"uvicorn"
  goto AFTER_HEALTH
)
ping -n 2 127.0.0.1 >nul
goto WAIT_HEALTH
:HEALTH_OK
echo [INFO] Backend health OK.
:AFTER_HEALTH

REM --- Fast-path smoke mode (skip all UI work; still emit launch URL) ---
if "%MIA_LAUNCH_SMOKE%"=="1" (
  echo [INFO] SMOKE mode enabled MIA_LAUNCH_SMOKE=1 skipping UI build/start
  if "%UI_MODE_STATIC%"=="1" (
    set "LAUNCH_URL=http://127.0.0.1:8000/"
  ) else (
    REM Backend only; still use backend root as launch URL for contract
    set "LAUNCH_URL=http://127.0.0.1:8000/"
  )
  echo [INFO] UI launch URL=%LAUNCH_URL%
  goto LAUNCH_END_OK
)

if "%MIA_LAUNCH_TEST%"=="1" goto TEST_MODE

REM --- UI open (dev when requested; static already prebuilt) ---
echo [TRACE] ui-open: begin static=%UI_MODE_STATIC%
if "%UI_MODE_STATIC%"=="1" goto OPEN_BROWSER
REM Dev server path
REM Allow overriding UI dev server port/host & browser via env:
REM   MIA_UI_PORT (default 3000)
REM   MIA_UI_HOST (default localhost)
REM   MIA_NO_BROWSER=1 disables auto-open
if "%MIA_UI_PORT%"=="" set MIA_UI_PORT=3000
if "%MIA_UI_HOST%"=="" set MIA_UI_HOST=localhost
if not exist chatgpt-design-app (echo [WARN] UI folder missing & goto AFTER_UI)
pushd chatgpt-design-app
where npm >nul 2>&1 || (echo [ERROR] npm not found in PATH. Install Node.js and retry. & popd & goto AFTER_UI)
if not exist node_modules (
  echo [INFO] Running npm install ^(first time^) ...
  call npm install > ..\%TMP_LAUNCH%\npm-install.log 2>&1 || (echo [ERROR] npm install failed. See ..\%TMP_LAUNCH%\npm-install.log & popd & goto AFTER_UI)
  echo [INFO] npm install completed.
) else (
  echo [INFO] node_modules present ^(skip install^).
)
for /f "delims=" %%P in ('where npm') do set NPM_EXE=%%P
set UI_LOG=%CD%\..\%TMP_LAUNCH%\ui.log
echo [INFO] Using NPM=%NPM_EXE%
echo [INFO] UI log: %UI_LOG%
(
  echo @echo off
  echo set CD_CUR=%%CD%%
  echo echo [DEBUG] CD=%%CD_CUR%% dev-mode
  echo call "%NPM_EXE%" run start ^> "%UI_LOG%" 2^>^&1
)> ..\%TMP_LAUNCH%\_ui_start.cmd
start "MIA UI" cmd /c ..\%TMP_LAUNCH%\_ui_start.cmd
popd
goto POST_UI_LAUNCH

:POST_UI_LAUNCH

REM Wait Vite (log poll up to 60 * ~2s =~120s)
set /a W=0
:WAIT_UI
if exist "%UI_LOG%" findstr /C:"dev server running at" "%UI_LOG%" >nul 2>&1 && goto UI_FROM_LOG
set /a W+=1
if %W% GEQ 60 goto UI_TIMEOUT
ping -n 2 127.0.0.1 >nul
goto WAIT_UI
:UI_FROM_LOG
echo [INFO] UI up after %W%s (log).
goto OPEN_BROWSER
:UI_TIMEOUT
echo [WARN] UI not up after %W%s (dev). Falling back to static build...
echo [DEBUG] --- UI LOG START ---
type %UI_LOG%
echo [DEBUG] --- UI LOG END ---
pushd chatgpt-design-app
if "%NPM_EXE%"=="" for /f "delims=" %%P in ('where npm') do set NPM_EXE=%%P
call "%NPM_EXE%" run build > ..\%TMP_LAUNCH%\ui-build.log 2>&1
if errorlevel 1 (
  echo [ERROR] UI static build failed. See ..\%TMP_LAUNCH%\ui-build.log
  popd
  goto OPEN_BROWSER
)
echo [INFO] Static build complete (fallback). Serving via backend on :8000
set UI_MODE_STATIC=1
popd
:OPEN_BROWSER
REM Assemble final LAUNCH_URL (no debug instrumentation)
if "%UI_MODE_STATIC%"=="1" set "LAUNCH_URL=http://127.0.0.1:8000/"
if not "%UI_MODE_STATIC%"=="1" set "LAUNCH_URL=http://%MIA_UI_HOST%:%MIA_UI_PORT%/"
REM Append ?dev=1 once unless disabled
if not "%MIA_DEV_DISABLE%"=="1" if "%LAUNCH_URL:?dev=1=%"=="%LAUNCH_URL%" set "LAUNCH_URL=%LAUNCH_URL%?dev=1" & echo [INFO] Dev flag appended ?dev=1
echo [INFO] UI launch URL=%LAUNCH_URL%
if "%UI_MODE_STATIC%"=="1" echo [HINT] Static UI mode (dist served by backend :8000)
if "%MIA_NO_BROWSER%"=="1" goto SKIP_BROWSER
start "" "%LAUNCH_URL%"
:SKIP_BROWSER
goto LAUNCH_END_OK
echo [INFO] Launch complete.
goto LAUNCH_END_OK

:AFTER_UI

:TEST_MODE
echo [INFO] TEST MODE: pipeline probe start
REM Build minimal dummy model manifest if none
if not exist llm\registry (mkdir llm\registry >nul 2>&1)
if not exist models mkdir models >nul 2>&1
if not exist llm\registry\_probe.yaml (
  echo id: probe-model>llm\registry\_probe.yaml
  echo family: dummy>>llm\registry\_probe.yaml
  echo role: primary>>llm\registry\_probe.yaml
  echo path: models/probe.bin>>llm\registry\_probe.yaml
  echo context_length: 2048>>llm\registry\_probe.yaml
  echo capabilities: [chat]>>llm\registry\_probe.yaml
  echo checksum_sha256: d41d8cd98f00b204e9800998ecf8427e>>llm\registry\_probe.yaml
  type nul > models\probe.bin
)

echo import http.client,json,sys> %TMP_LAUNCH%\_probe.py
echo conn=http.client.HTTPConnection('127.0.0.1',8000,timeout=15)>> %TMP_LAUNCH%\_probe.py
echo body=json.dumps({'session_id':'s1','model':'probe-model','prompt':'hello'}).encode()>> %TMP_LAUNCH%\_probe.py
echo conn.request('POST','/generate',body,{'Content-Type':'application/json'})>> %TMP_LAUNCH%\_probe.py
echo resp=conn.getresponse()>> %TMP_LAUNCH%\_probe.py
echo data=resp.read(4096)>> %TMP_LAUNCH%\_probe.py
echo sys.exit(0 if b'event: token' in data else 2)>> %TMP_LAUNCH%\_probe.py
"%VENV_PY%" %TMP_LAUNCH%\_probe.py || (echo [ERROR] Pipeline token probe FAILED & exit /b 1)
echo [INFO] Pipeline token probe OK.
if exist chatgpt-design-app (
  pushd chatgpt-design-app & call npm run build || (echo [ERROR] Frontend build failed & popd & exit /b 1) & popd
  echo [INFO] Frontend build OK.
) else (echo [WARN] UI folder missing (skipped build))
echo [INFO] TEST MODE success.

:LAUNCH_END_OK
echo [TRACE] end: success
if "%MIA_LAUNCH_STAY%"=="" set MIA_LAUNCH_STAY=0
if "%MIA_LAUNCH_STAY%"=="1" (
  echo.
  echo [INFO] Launcher done. Press any key to close this window.
  pause >nul
)
goto END_ALL

:LAUNCH_END_ERR
echo [TRACE] end: error
set EXITCODE=1
if "%MIA_LAUNCH_STAY%"=="" set MIA_LAUNCH_STAY=0
if "%MIA_LAUNCH_STAY%"=="1" (
  echo.
  echo [ERROR] Launch failed. Press any key to close this window.
  pause >nul
)

:END_ALL
REM (Optional) cleanup temp scripts
REM rmdir /s /q %TMP_LAUNCH% >nul 2>&1
endlocal
