@echo off
REM Build llama-cpp-python with CUDA using MSVC toolchain (both GGML_CUDA & LLAMA_CUDA flags)
setlocal enableextensions EnableDelayedExpansion
echo [STEP] Initializing MSVC environment...
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul || goto :error
echo [OK] MSVC env ready.

echo [STEP] Preparing environment variables...
REM Force prefer CUDA 13.0 if installed and no explicit override requested
if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0\bin\nvcc.exe" (
	if /I not "%CUDA_PATH%"=="C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0" (
		echo [INFO] Auto-selecting CUDA v13.0 toolkit
		set "CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0"
	)
)
echo [DEBUG] Pre-check CUDA_PATH=%CUDA_PATH%
if not defined CUDA_PATH (
	echo [WARN] CUDA_PATH not set. Attempting auto-detect...
	for %%V in (13.0 12.5 12.4 12.3 12.2 12.1) do (
		if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v%%V\bin\nvcc.exe" (
			set "CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v%%V"
			echo [INFO] Detected CUDA at %CUDA_PATH%
			goto :after_cuda_detect
		)
	)
	echo [ERROR] CUDA toolkit not found. Please install CUDA >=12.4 (or 13.x) and set CUDA_PATH env var.
	exit /b 2
)
:after_cuda_detect
echo [DEBUG] Passed auto-detect block.
echo [INFO] Using CUDA_PATH=%CUDA_PATH%
echo [DEBUG] PATH(head)=%PATH:~0,120%
echo [STEP] Checking nvcc availability early...
echo [STEP] where nvcc
where nvcc || echo [ERROR] nvcc not found in PATH
echo [STEP] invoking nvcc --version
"%CUDA_PATH%\bin\nvcc.exe" --version || goto :error
echo [STEP] nvcc OK, proceeding to compose CMake args
REM Force prefer new CUDA over legacy installs (12.1 still present system-wide)
set CUDA_HOME=%CUDA_PATH%
set CUDAToolkit_ROOT=%CUDA_PATH%
set CUDA_TOOLKIT_ROOT_DIR=%CUDA_PATH%
REM Wipe legacy version vars that can mislead CMake (best effort)
set CUDA_PATH_V12_1=
REM Prepend new toolkit bin & libnvvp to PATH (must be first, not last)
set PATH=%CUDA_PATH%\bin;%CUDA_PATH%\libnvvp;%PATH%
echo Using CUDA_PATH=%CUDA_PATH%
echo [STEP] where nvcc (post PATH prepend)
where nvcc
"%CUDA_PATH%\bin\nvcc.exe" --version || goto :error
REM Explicit arch for RTX 4070 (SM89) instead of 'native' to avoid mis-detection
REM Base CMake args (include legacy -DLLAMA_CUBLAS=on for broader version compat)
set CMAKE_ARGS=-DGGML_CUDA=on -DLLAMA_CUBLAS=on -DLLAMA_CUDA_F16=on -DLLAMA_BUILD_TESTS=off -DCMAKE_CUDA_ARCHITECTURES=89 -DCUDAToolkit_ROOT="%CUDA_PATH%" -DCUDA_TOOLKIT_ROOT_DIR="%CUDA_PATH%" -DCMAKE_VERBOSE_MAKEFILE=ON

REM Optional: enable Flash / Fused MHA (env MIA_FLASH_ATTENTION=1)
if "%MIA_FLASH_ATTENTION%"=="1" (
	echo [OPT] Requesting FMHA (Flash Attention)
	REM New flag name in recent llama.cpp is GGML_CUDA_FMHA
	set CMAKE_ARGS=%CMAKE_ARGS% -DGGML_CUDA_FMHA=on
	REM Keep backward fallback ONLY if older name still recognized (ignored silently otherwise)
	set CMAKE_ARGS=%CMAKE_ARGS% -DGGML_CUDA_FLASH_ATTENTION=on
)
REM Optional: force MMQ kernels (env MIA_FORCE_MMQ=1)
if "%MIA_FORCE_MMQ%"=="1" (
	echo [OPT] Forcing MMQ kernels
	set CMAKE_ARGS=%CMAKE_ARGS% -DGGML_CUDA_FORCE_MMQ=on
)
set CMAKE_GENERATOR=Ninja
set FORCE_CMAKE=1
set CMAKE_CUDA_COMPILER=%CUDA_PATH%\bin\nvcc.exe
echo CMAKE_ARGS=%CMAKE_ARGS%
echo [INFO] (Set MIA_FLASH_ATTENTION=1 to request FMHA; MIA_LLAMA_CPP_PY_REF=main for latest git)
set SKBUILD_CONFIGURE_OPTIONS=%CMAKE_ARGS%
set SKBUILD_CMAKE_ARGS=%CMAKE_ARGS%
set SKBUILD_BUILD_OPTIONS=--verbose
set SCikit_BUILD_VERBOSE=1
set SKBUILD_VERBOSE=1
set VERBOSE=1

echo [STEP] Upgrading pip/setuptools/wheel...
call %~dp0..\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel >nul || goto :error

echo [STEP] Installing build prerequisites (cmake, ninja, scikit-build-core)...
call %~dp0..\.venv\Scripts\pip.exe install -U cmake ninja scikit-build-core >nul || goto :error
echo [DEBUG] Versions: & call %~dp0..\.venv\Scripts\python.exe -c "import cmake,sys;import importlib,platform;import pkgutil;import subprocess,os;print('python',sys.version.split()[0]);print('cmake',cmake.__version__);print('platform',platform.platform());" || goto :error

echo [STEP] Cleaning any previous llama_cpp_python artifacts...
del /q %~dp0..\.venv\Lib\site-packages\llama_cpp_python* 2>nul

echo [STEP] Building llama-cpp-python (CUDA)...
REM Provide Python executable explicitly for CMake (helps when multiple versions present)
set Python_EXECUTABLE=%~dp0..\.venv\Scripts\python.exe
REM NOTE: keeping within <0.4.0 per requirements.txt, allow git ref override for bleeding-edge FMHA
if defined MIA_LLAMA_CPP_PY_REF (
	echo [STEP] Installing llama-cpp-python from git ref %MIA_LLAMA_CPP_PY_REF%
	set PIP_VERBOSE=-v -v
	echo [DEBUG] Using CMAKE_ARGS=%CMAKE_ARGS%
	echo [DEBUG] Invoking pip with verbosity for detailed CMake output
	call %~dp0..\.venv\Scripts\pip.exe install %PIP_VERBOSE% --no-cache-dir --force-reinstall --no-build-isolation git+https://github.com/abetlen/llama-cpp-python@%MIA_LLAMA_CPP_PY_REF% || goto :error
) else (
	echo [STEP] Installing llama-cpp-python==0.3.16 (pinned) with verbosity
	set PIP_VERBOSE=-v -v
	echo [DEBUG] Using CMAKE_ARGS=%CMAKE_ARGS%
	call %~dp0..\.venv\Scripts\pip.exe install %PIP_VERBOSE% --no-cache-dir --force-reinstall --no-build-isolation llama-cpp-python==0.3.16 || goto :error
)

echo [STEP] Verifying build exposes offload capability...
call %~dp0..\.venv\Scripts\python.exe -c "import llama_cpp as lc,sys;print('supports_gpu_offload=',lc.llama_supports_gpu_offload());" || goto :error

echo [STEP] Post-build diagnostics (searching for FMHA / FLASH tokens)...
for /f "delims=" %%i in ('dir /b /s %~dp0..\.venv\Lib\site-packages\llama_cpp_python* 2^>nul') do (
  findstr /I /C:"FLASH_ATTENTION" /C:"FMHA" "%%i" >nul 2>nul && echo [HIT] %%i contains FLASH/FMHA token
)

echo [STEP] Attempting runtime introspection of compiled symbols...
call %~dp0..\.venv\Scripts\python.exe -c "import llama_cpp,inspect,sys;import re;import pkgutil;import pathlib;import importlib;print('llama_cpp.__file__', llama_cpp.__file__);print('version_attr',getattr(llama_cpp,'__version__','?'));from llama_cpp import llama_cpp as core; attrs=[a for a in dir(core) if ('FLASH' in a or 'FMHA' in a or 'ATTN' in a)]; print('core_symbol_candidates',attrs[:50]);" || goto :error

echo BUILD_SUCCESS
exit /b 0
:error
echo BUILD_FAILED %ERRORLEVEL%
exit /b %ERRORLEVEL%
