import os
import time
from pathlib import Path
import json

import pytest

from core.llm.factory import get_model, clear_provider_cache
from core.registry.loader import clear_manifest_cache
from core.events import on, reset_listeners_for_tests


@pytest.mark.performance
def test_perf_gpt_oss_real():
    """Real performance smoke for gpt-oss (not fake).

    Skips automatically if:
      - llama_cpp not installed
      - model file missing
      - env MIA_REAL_PERF != '1' (explicit opt-in safeguard)
    Measures:
      - load_ms from ModelLoaded event
      - generation latency + tokens/s for 64 tokens
    """
    if os.environ.get("MIA_REAL_PERF") != "1":
        pytest.skip("Set MIA_REAL_PERF=1 to run real performance test")

    model_id = "gpt-oss-20b-mxfp4"
    repo_root = Path(".").resolve()
    manifest_path = repo_root / "llm" / "registry" / f"{model_id}.yaml"
    if not manifest_path.exists():
        pytest.skip("Manifest for gpt-oss not found")
    weights_path = (
        repo_root
        / "models"
        / "gpt-oss-20b-GGUF"
        / "gpt-oss-20b-MXFP4.gguf"
    )
    if not weights_path.exists():
        pytest.skip(
            "Model weights file missing; place GGUF file to run real perf"
        )

    try:
        import llama_cpp  # noqa: F401
    except Exception:  # noqa: BLE001
        pytest.skip("llama_cpp not installed")

    events = []
    on(lambda n, p: events.append((n, p)))

    clear_manifest_cache()
    clear_provider_cache()

    # Load model explicitly (isolate load_ms rather than mixing with first gen)
    prov = get_model(model_id, repo_root=repo_root)
    t0 = time.time()
    prov.load()
    load_latency = (time.time() - t0) * 1000

    # Extract ModelLoaded event latency if available
    emitted_load_ms = None
    for name, payload in events:
        if name == "ModelLoaded" and payload.get("model_id") == model_id:
            emitted_load_ms = payload.get("load_ms")
            break

    # Generation test
    prompt = "Explain the importance of reproducible configurations in AI systems."  # noqa: E501
    gen_start = time.time()
    out = prov.generate(prompt, max_tokens=64)
    gen_latency = time.time() - gen_start
    tokens_out = len(out.split())
    tokens_per_s = tokens_out / gen_latency if gen_latency > 0 else 0.0

    # Basic assertions (non-zero output)
    assert tokens_out > 0
    # Soft expectations (do not fail hard; capture metrics)
    print(
        f"LOAD_MS={load_latency:.0f} EVENT_LOAD_MS={emitted_load_ms} "
        f"TOKENS={tokens_out} GEN_LATENCY_S={gen_latency:.2f} "
        f"TOKENS_PER_S={tokens_per_s:.2f}"
    )  # noqa: T201,E501

    # If tokens/s extremely low, flag but don't fail (informational)
    if tokens_per_s < 1:  # arbitrary minimal threshold just for visibility
        pytest.xfail(f"Low throughput: {tokens_per_s:.2f} tokens/s")

    # Optional JSON report
    out_path = os.environ.get("MIA_PERF_JSON")
    if not out_path:
        # default location
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        out_path = reports_dir / f"perf_{model_id}.json"
    data = {
        "model_id": model_id,
        "load_ms": load_latency,
        "event_load_ms": emitted_load_ms,
        "gen_latency_s": gen_latency,
        "tokens_out": tokens_out,
        "tokens_per_s": tokens_per_s,
    }
    Path(out_path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    reset_listeners_for_tests()
