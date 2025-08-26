@echo off
REM Simplified build script with CUDA v13.0 and conditional FMHA (git main) support.
setlocal enableextensions

REM --- Configurable Section -------------------------------------------------
if "%MIA_LLAMA_CPP_PY_REF%"=="" (
  REM Default to main to support FMHA; override by setting MIA_LLAMA_CPP_PY_REF or PIN_VERSION=1
  set "MIA_LLAMA_CPP_PY_REF=main"
)
if not "%PIN_VERSION%"=="1" (
  set "USE_GIT=1"
) else (
  set "USE_GIT="
)

set "CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0"
if not exist "%CUDA_PATH%\bin\nvcc.exe" (
  echo [ERROR] nvcc not found at %CUDA_PATH%\bin\nvcc.exe
  exit /b 2
)
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 3
echo [INFO] Using CUDA_PATH=%CUDA_PATH%
"%CUDA_PATH%\bin\nvcc.exe" --version || exit /b 4

REM Version-dependent flags (new upstream uses GGML_CUDA / FMHA)
set CMAKE_GENERATOR=Ninja
if defined USE_GIT (
  REM Upstream main: use GGML_* flags only (remove deprecated flags; FLASH_ATTENTION deprecated)
  set "CMAKE_ARGS=-DGGML_CUDA=on -DGGML_CUDA_FMHA=on -DCMAKE_CUDA_ARCHITECTURES=89 -DCMAKE_BUILD_TYPE=Release -DCUDAToolkit_ROOT=%CUDA_PATH% -DCUDA_TOOLKIT_ROOT_DIR=%CUDA_PATH% -DCMAKE_VERBOSE_MAKEFILE=ON"
) else (
  REM Pinned legacy build (no FMHA expected)
  set "CMAKE_ARGS=-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89 -DCMAKE_BUILD_TYPE=Release -DCUDAToolkit_ROOT=%CUDA_PATH% -DCUDA_TOOLKIT_ROOT_DIR=%CUDA_PATH% -DCMAKE_VERBOSE_MAKEFILE=ON"
)
echo [INFO] CMAKE_GENERATOR=%CMAKE_GENERATOR%
echo [INFO] CMAKE_ARGS=%CMAKE_ARGS%
set SKBUILD_CONFIGURE_OPTIONS=%CMAKE_ARGS%
set SKBUILD_CMAKE_ARGS=%CMAKE_ARGS%
set VERBOSE=1

echo [STEP] Ensuring build toolchain (pip, cmake, ninja)...
call %~dp0..\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel >nul || exit /b 5
call %~dp0..\.venv\Scripts\pip.exe install -U cmake ninja scikit-build-core >nul || exit /b 6

echo [STEP] Removing any existing llama_cpp_python packages...
del /q %~dp0..\.venv\Lib\site-packages\llama_cpp_python* 2>nul
del /q %~dp0..\.venv\Lib\site-packages\llama_cpp* 2>nul
echo [INFO] Starting build at %TIME%

if defined USE_GIT (
  echo [STEP] Installing llama-cpp-python from git ref %MIA_LLAMA_CPP_PY_REF%
  call %~dp0..\.venv\Scripts\pip.exe install -v -v --no-cache-dir --force-reinstall --no-build-isolation git+https://github.com/abetlen/llama-cpp-python@%MIA_LLAMA_CPP_PY_REF% || (echo [ERROR] pip install failed & exit /b 7)
) else (
  echo [STEP] Installing pinned llama-cpp-python==0.3.16 (no FMHA expected)
  call %~dp0..\.venv\Scripts\pip.exe install -v -v --no-cache-dir --force-reinstall --no-build-isolation llama-cpp-python==0.3.16 || (echo [ERROR] pip install failed & exit /b 7)
)

echo [INFO] Build finished at %TIME%

echo [STEP] Runtime probe...
call %~dp0..\.venv\Scripts\python.exe -c "import llama_cpp,sys;from llama_cpp import llama_cpp as core;print('llama_cpp.__file__=', llama_cpp.__file__);print('version=',getattr(llama_cpp,'__version__','?'));print('supports_gpu_offload=',getattr(llama_cpp,'llama_supports_gpu_offload',lambda:None)());si=getattr(core,'llama_print_system_info',None);print('system_info_present=',bool(si));print(si().decode() if si else '');" || exit /b 8

echo BUILD_SIMPLE_DONE
exit /b 0
