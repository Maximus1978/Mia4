"""Preflight check for CUDA toolkit completeness and llama.cpp GPU offload.

Usage (PowerShell example):
    # Example set shorter path (adjust to real install)
    $env:CUDA_PATH="C:\\CUDA\\v13.0";
    # adjust path above if different version
    python scripts/preflight_cuda_runtime.py

Checks:
  - CUDA_PATH set & exists
  - Presence of cudart & cublas DLLs (version inferred from directory)
  - Prints which directories are scanned
    - Adds DLL dirs, imports llama_cpp, reports llama_supports_gpu_offload()
  - Non-zero exit if any critical component missing or GPU offload unsupported
"""
from __future__ import annotations

import os
from pathlib import Path

REQUIRED_DLL_BASENAMES = [
    # adjust suffix if targeting different toolkit version
    "cudart64_13.dll",
    "cublas64_13.dll",
    "cublasLt64_13.dll",
]


def main() -> int:
    cuda_root = os.getenv("CUDA_PATH") or os.getenv("CUDA_HOME")
    if not cuda_root:
        print("[FAIL] CUDA_PATH not set")
        return 2
    root_path = Path(cuda_root)
    if not root_path.exists():
        print(f"[FAIL] CUDA_PATH does not exist: {root_path}")
        return 2
    print(f"[INFO] CUDA_PATH={root_path}")
    search_dirs = [root_path / "bin" / "x64", root_path / "bin"]
    found = {}
    for dll in REQUIRED_DLL_BASENAMES:
        found[dll] = None
        for d in search_dirs:
            p = d / dll
            if p.exists():
                found[dll] = p
                break
    missing = [k for k, v in found.items() if v is None]
    for k, v in found.items():
        if v is None:
            print(f"[MISS] {k}")
        else:
            print(f"[OK]   {k} -> {v}")
    if missing:
        print("[FAIL] Missing CUDA runtime DLLs; install full Toolkit.")
        return 3
    # Add dll directories (Python 3.8+)
    for d in search_dirs:
        if d.is_dir():
            try:
                os.add_dll_directory(str(d))  # type: ignore[attr-defined]
            except Exception:
                pass
    try:
        import llama_cpp  # type: ignore
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] Import llama_cpp failed: {e}")
        return 4
    try:
        supports = llama_cpp.llama_supports_gpu_offload()
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] Query llama_supports_gpu_offload failed: {e}")
        return 5
    print(
        f"[INFO] llama_cpp.__version__="
        f"{getattr(llama_cpp,'__version__',None)}"
    )
    print(f"[INFO] supports_gpu_offload={supports}")
    if not supports:
        print("[FAIL] GPU offload not supported; rebuild required.")
        return 6
    print("[PASS] CUDA runtime & llama.cpp GPU offload OK")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
