@echo off
setlocal
if exist .venv goto :done
python -m venv .venv || (echo Failed to create venv & exit /b 1)
:done
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
if exist requirements.lock (
  python -m pip install -r requirements.lock || goto :eof
) else if exist requirements.txt (
  python -m pip install -r requirements.txt || goto :eof
)
endlocal
