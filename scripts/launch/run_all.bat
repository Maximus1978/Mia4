@echo off
setlocal ENABLEDELAYEDEXPANSION
echo [TRACE] enter: run_all.bat
REM ===== MIA4 Unified Launcher =====
REM Usage: run_all.bat [user|admin]  (env MIA_LAUNCH_TEST=1 for headless probe mode)

cd /d "%~dp0..\.." || (echo [ERROR] cd repo root failed & goto LAUNCH_END_ERR)
echo [TRACE] cwd=%CD%
set MODE=%1
if "%MODE%"=="" set MODE=user
REM UI mode now uses non-config env var MIA_UI_MODE to avoid config schema extra keys
if /I "%MODE%"=="admin" (
  set MIA_UI_MODE=admin
  set MIA__logging__level=debug
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
if "%MIA_UI_STATIC%"=="" set MIA_UI_STATIC=1
if "%MIA_UI_STATIC%"=="1" (
  if exist chatgpt-design-app (
    pushd chatgpt-design-app
    where npm >nul 2>&1 || (echo [ERROR] npm not found in PATH. Install Node.js and retry. & popd)
    if not exist node_modules (
      echo [INFO] Running npm install ^(first time^)
      call npm install > ..\%TMP_LAUNCH%\npm-install.log 2>&1 || (echo [ERROR] npm install failed. See ..\%TMP_LAUNCH%\npm-install.log & popd)
      if errorlevel 1 goto START_BACKEND
      echo [INFO] npm install completed.
    ) else (
      echo [INFO] node_modules present ^(skip install^).
    )
    for /f "delims=" %%P in ('where npm') do set NPM_EXE=%%P
    echo [INFO] Building static UI ^(pre-backend^)
    call "%NPM_EXE%" run build > ..\%TMP_LAUNCH%\ui-build.log 2>&1
    if errorlevel 1 (
      echo [ERROR] UI build failed. See ..\%TMP_LAUNCH%\ui-build.log
      popd
    ) else (
      echo [INFO] Static build complete ^(will be served by backend on :8000^)
      set UI_MODE_STATIC=1
      popd
    )
  ) else (
    echo [WARN] UI folder missing ^(skip build^)
  )
)

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
start "MIA Backend" cmd /k "%TMP_LAUNCH%\backend_loop.cmd"
goto BACKEND_STARTED
:BACKEND_SINGLE
echo [INFO] Backend supervise disabled.
(
  echo @echo off
  echo set PYTHONPATH=%PYTHONPATH%
  echo echo [BACKEND] starting ^>^> "%BACKEND_LOG%"
  echo call "%VENV_PY%" -m uvicorn mia4.api.app:app --host 127.0.0.1 --port 8000 --no-access-log ^>^> "%BACKEND_LOG%" 2^>^&1
) > "%TMP_LAUNCH%\backend_once.cmd"
start "MIA Backend" cmd /k "%TMP_LAUNCH%\backend_once.cmd"
:BACKEND_STARTED

REM --- Wait health (5s) ---
echo [TRACE] health: wait
set /a TRY=0
echo import urllib.request,sys> %TMP_LAUNCH%\_health.py
echo try:>> %TMP_LAUNCH%\_health.py
echo ^    urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1)>> %TMP_LAUNCH%\_health.py
echo ^    sys.exit(0)>> %TMP_LAUNCH%\_health.py
echo except Exception: sys.exit(1)>> %TMP_LAUNCH%\_health.py
:WAIT_HEALTH
"%VENV_PY%" %TMP_LAUNCH%\_health.py >nul 2>&1 && goto HEALTH_OK
set /a TRY+=1
if %TRY% GEQ 20 (
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
  echo echo [DEBUG] CD=%%CD_CUR%% (dev)
  echo call "%NPM_EXE%" run start ^> "%UI_LOG%" 2^>^&1
)> ..\%TMP_LAUNCH%\_ui_start.cmd
start "MIA UI" cmd /c ..\%TMP_LAUNCH%\_ui_start.cmd
popd
goto POST_UI_LAUNCH

:POST_UI_LAUNCH

REM Wait Vite (30s)
set /a W=0
echo import urllib.request,sys> %TMP_LAUNCH%\_uiwait.py
echo ok=0>> %TMP_LAUNCH%\_uiwait.py
echo for host in ('http://127.0.0.1:%MIA_UI_PORT%','http://%MIA_UI_HOST%:%MIA_UI_PORT%'):>> %TMP_LAUNCH%\_uiwait.py
echo ^    try: urllib.request.urlopen(host,timeout=1); ok=1; break>> %TMP_LAUNCH%\_uiwait.py
echo ^    except Exception: pass>> %TMP_LAUNCH%\_uiwait.py
echo sys.exit(0 if ok else 1)>> %TMP_LAUNCH%\_uiwait.py
:WAIT_UI
"%VENV_PY%" %TMP_LAUNCH%\_uiwait.py >nul 2>&1 && goto UI_OK
findstr /C:"dev server running at" "%UI_LOG%" >nul 2>&1 && goto UI_FROM_LOG
set /a W+=1
if %W% GEQ 60 (
  echo [WARN] UI not up after %W%s (dev). Falling back to static build...
  echo [DEBUG] --- UI LOG START ---
  type %UI_LOG%
  echo [DEBUG] --- UI LOG END ---
  pushd chatgpt-design-app
  call "%NPM_EXE%" run build > ..\%TMP_LAUNCH%\ui-build.log 2>&1
  if errorlevel 1 (
    echo [ERROR] UI static build failed. See ..\%TMP_LAUNCH%\ui-build.log
    popd
    goto OPEN_BROWSER
  )
  echo [INFO] Static build complete (fallback). Serving via backend on :8000
  set UI_MODE_STATIC=1
  popd
  goto OPEN_BROWSER
)
ping -n 2 127.0.0.1 >nul
goto WAIT_UI
:UI_OK
echo [INFO] UI up after %W%s (probe).
goto OPEN_BROWSER
:UI_FROM_LOG
echo [INFO] UI up after %W%s (log).
:OPEN_BROWSER
if "%UI_MODE_STATIC%"=="1" (
  set LAUNCH_URL=http://127.0.0.1:8000/
) else (
  set LAUNCH_URL=http://%MIA_UI_HOST%:%MIA_UI_PORT%/
)
echo [INFO] UI launch URL=%LAUNCH_URL%
if "%MIA_NO_BROWSER%"=="1" (
  echo [INFO] Browser auto-open disabled (MIA_NO_BROWSER=1).
) else (
  REM Browser selection: if MIA_BROWSER=chrome try explicit chrome.exe paths
  set BROWSER_EXE=
  if /I "%MIA_BROWSER%"=="chrome" (
    if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set BROWSER_EXE="C:\Program Files\Google\Chrome\Application\chrome.exe"
    if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set BROWSER_EXE="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    if defined BROWSER_EXE (
      echo [INFO] Launching Chrome via %BROWSER_EXE%
      start "MIA UI" %BROWSER_EXE% "%LAUNCH_URL%"
    ) else (
      echo [WARN] Chrome not found, falling back to default handler.
      cmd /c start "MIA UI" "%LAUNCH_URL%"
    )
  ) else (
    REM Default handler (system associated browser)
    cmd /c start "MIA UI" "%LAUNCH_URL%"
  )
  ping -n 2 127.0.0.1 >nul
  if not "%MIA_NO_BROWSER%"=="1" (
    if defined BROWSER_EXE (
      start "MIA UI" %BROWSER_EXE% "%LAUNCH_URL%"
    ) else (
      cmd /c start "MIA UI" "%LAUNCH_URL%"
      REM Additional fallbacks to ensure default browser opens on some shells
      REM 1) PowerShell Start-Process (ignores errors quietly)
      powershell -NoLogo -NoProfile -Command "Start-Process '%LAUNCH_URL%'" 2>nul
      REM 2) Legacy Windows handler via rundll32 (final fallback)
      if exist "%SystemRoot%\System32\rundll32.exe" (
        rundll32 url.dll,FileProtocolHandler "%LAUNCH_URL%" 2>nul
      )
    )
  )
)
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
if "%MIA_LAUNCH_STAY%"=="" set MIA_LAUNCH_STAY=1
if "%MIA_LAUNCH_STAY%"=="1" (
  echo.
  echo [INFO] Launcher done. Press any key to close this window.
  pause >nul
)
goto END_ALL

:LAUNCH_END_ERR
echo [TRACE] end: error
set EXITCODE=1
if "%MIA_LAUNCH_STAY%"=="" set MIA_LAUNCH_STAY=1
if "%MIA_LAUNCH_STAY%"=="1" (
  echo.
  echo [ERROR] Launch failed. Press any key to close this window.
  pause >nul
)

:END_ALL
REM (Optional) cleanup temp scripts
REM rmdir /s /q %TMP_LAUNCH% >nul 2>&1
endlocal
