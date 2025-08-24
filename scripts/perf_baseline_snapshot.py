"""Capture a baseline snapshot of core generation metrics.

Uses events (GenerationFinished) to obtain authoritative output token counts
instead of naive whitespace split, producing a JSON artifact consumed later
for regression comparison after config refactor.
"""
from __future__ import annotations

import json
import time
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config.loader import get_config, clear_config_cache  # noqa: E402
from core.llm.factory import get_model, clear_provider_cache  # noqa: E402
from core.events import subscribe, GenerationFinished  # noqa: E402

OUT = pathlib.Path("reports/perf_baseline_snapshot.json")


def measure(max_tokens: int = 64):
    clear_config_cache()
    cfg = get_config()
    clear_provider_cache()
    provider = get_model(cfg.llm.primary.id, skip_checksum=True)
    captured: dict[str, int] = {}

    def _on(ev):  # noqa: ANN001
        if isinstance(ev, GenerationFinished):
            captured["output_tokens"] = ev.output_tokens
            captured["latency_ms"] = ev.latency_ms

    unsubscribe = subscribe(_on)
    t0 = time.time()
    text = provider.generate("Baseline snapshot test.", max_tokens=max_tokens)
    total = time.time() - t0
    unsubscribe()
    out_tokens = captured.get("output_tokens") or len(text.split())
    return {
        "model_id": provider.info().id,
        "target_max_tokens": max_tokens,
        "output_tokens": out_tokens,
        "latency_s": round(total, 3),
        "tps": round(out_tokens / total, 3) if total > 0 else None,
        "event_latency_ms": captured.get("latency_ms"),
        "timestamp": time.time(),
    }


def main():  # noqa: D401
    result = measure(64)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
