"""CPU baseline measurement script.

Purpose (Step 10.1):
  - Measure first load latency (ms) for primary model on CPU (n_gpu_layers=0)
  - Measure generation latency & tokens/s for a short prompt (64 output tokens)
  - Persist JSON report to reports/perf_cpu_baseline.json (or MIA_PERF_OUT)

Usage (PowerShell):
  $env:MIA_LLAMA_FAKE="0"            # real run
  $env:MIA__LLM__PRIMARY__N_GPU_LAYERS="0"
  python scripts/perf_cpu_baseline.py

Env overrides:
  MIA_PERF_OUT - custom output path.

Report schema:
  {
    "model_id": str,
    "mode": "cpu",
    "load_ms": int,
    "gen_latency_s": float,
    "tokens_out": int,
    "tokens_per_s": float,
    "commit": str | null,
    "llama_cpp_version": str | null,
    "fake": bool
  }
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List, Tuple

"""NOTE: Adds project root to sys.path for direct script execution.
Prefer future packaging (editable install) to remove this hack.
"""
import sys
from pathlib import Path as _P
_ROOT = _P(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:  # ensure project root for 'core' imports
    sys.path.insert(0, str(_ROOT))

from core.llm.factory import get_model, clear_provider_cache  # noqa: E402
from core.registry.loader import clear_manifest_cache  # noqa: E402
from core.events import on, reset_listeners_for_tests  # noqa: E402


def _git_commit() -> str | None:
    try:
        import subprocess  # noqa: PLC0415

        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:  # noqa: BLE001
        return None


def _llama_version() -> str | None:
    try:  # noqa: SIM105
        import llama_cpp  # type: ignore  # noqa: PLC0415

        return getattr(llama_cpp, "__version__", None)
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    fake = os.getenv("MIA_LLAMA_FAKE", "0") == "1"
    model_id = os.getenv("MIA_PRIMARY_ID", "gpt-oss-20b-mxfp4")
    prompt = (
        "Explain why reproducible configuration improves reliability in AI "
        "systems."
    )
    out_path = os.getenv("MIA_PERF_OUT") or Path("reports") / (
        "perf_cpu_baseline.json"
    )
    if isinstance(out_path, str):
        out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Capture events for load_ms (prefer event timing over manual if present)
    events: List[Tuple[str, dict]] = []
    on(lambda n, p: events.append((n, p)))
    clear_manifest_cache()
    clear_provider_cache()
    # Late import to ensure env overrides applied
    from core.config.loader import get_config

    cfg = get_config()
    prov = get_model(model_id)
    t0 = time.time()
    prov.load()
    load_ms_manual = int((time.time() - t0) * 1000)
    load_ms = load_ms_manual
    for name, payload in events:
        if name == "ModelLoaded" and payload.get("model_id") == model_id:
            load_ms = payload.get("load_ms", load_ms_manual)
            break

    # Generation (fixed max_tokens=64)
    gen_t0 = time.time()
    out_text = prov.generate(prompt, max_tokens=64)
    gen_latency = time.time() - gen_t0
    tokens_out = len(out_text.split())
    tokens_per_s = tokens_out / gen_latency if gen_latency > 0 else 0.0

    report = {
        "model_id": model_id,
        "mode": "cpu",
        "load_ms": load_ms,
        "gen_latency_s": round(gen_latency, 4),
        "tokens_out": tokens_out,
        "tokens_per_s": round(tokens_per_s, 2),
        "commit": _git_commit(),
        "llama_cpp_version": _llama_version(),
        "fake": fake,
        "cfg_max_output_tokens": cfg.llm.primary.max_output_tokens,
    }
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))  # noqa: T201
    reset_listeners_for_tests()
    if fake:
        print("[WARN] Running in fake mode; metrics not representative.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
