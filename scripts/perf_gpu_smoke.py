"""GPU smoke performance test (Step 10.3).

Goals:
- Load primary model with configurable n_gpu_layers (auto or int) and
    small generation.
- Capture load_ms (event) and generation tokens/s for 64 tokens.
- Output JSON report to reports/perf_gpu_smoke.json (override via
    MIA_PERF_OUT).

Assumptions:
- llama-cpp-python installed with GPU support (CUDA / OpenCL depending
    on build).
- Environment variable MIA_LLAMA_FAKE=0 for real run.

Usage (PowerShell example):

        $env:MIA_LLAMA_FAKE="0"
        $env:MIA__LLM__PRIMARY__N_GPU_LAYERS="auto"  # or specific number
        python scripts/perf_gpu_smoke.py

"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Ensure project root on sys.path (sibling of 'scripts')
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.config import get_config  # noqa: E402
from core.llm.factory import get_model, clear_provider_cache  # noqa: E402
from core.registry.loader import clear_manifest_cache  # noqa: E402
from core.events import on, reset_listeners_for_tests  # noqa: E402


def main() -> None:
    cfg = get_config()
    # RootConfig object access
    model_id = cfg.llm.primary.id

    # Force real mode
    os.environ.setdefault("MIA_LLAMA_FAKE", "0")

    # Collect events
    events: list[tuple[str, dict]] = []
    on(lambda n, p: events.append((n, p)))

    clear_manifest_cache()
    clear_provider_cache()

    prov = get_model(model_id)

    # Explicit load for isolated measurement
    t0 = time.time()
    prov.load()
    manual_load_ms = int((time.time() - t0) * 1000)

    emitted_load_ms = None
    for name, payload in events:
        if name == "ModelLoaded" and payload.get("model_id") == model_id:
            emitted_load_ms = payload.get("load_ms")
            break

    prompt = "List three key benefits of GPU offloading for large language models."  # noqa: E501
    gen_start = time.time()
    out = prov.generate(prompt, max_tokens=64)
    gen_latency_s = time.time() - gen_start
    tokens_out = len(out.split())
    tokens_per_s = tokens_out / gen_latency_s if gen_latency_s > 0 else 0.0

    report = {
        "stage": "gpu_smoke",
        "model_id": model_id,
        "n_gpu_layers": cfg.llm.primary.n_gpu_layers,
        "load_ms_manual": manual_load_ms,
        "load_ms_event": emitted_load_ms,
        "gen_latency_s": gen_latency_s,
        "tokens_out": tokens_out,
        "tokens_per_s": tokens_per_s,
        "timestamp": time.time(),
    }

    out_path_env = os.environ.get("MIA_PERF_OUT")
    out_path = (
        Path(out_path_env)
        if out_path_env
        else Path("reports/perf_gpu_smoke.json")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))  # noqa: T201

    reset_listeners_for_tests()


if __name__ == "__main__":  # pragma: no cover
    main()
