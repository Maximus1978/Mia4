"""Long context saturation test (Step 10.5).

Purpose:
  Measure generation latency & throughput (tokens/s) for a longer output
  (default 512 tokens) across several n_gpu_layers configs vs short smoke runs.

Env overrides:
  MIA_LONG_TOKENS   (int, default 512)
  MIA_LONG_LAYERS   (comma list, default "0,6,12,auto")
  MIA_PERF_OUT      (path, default reports/perf_long_context.json)

Output JSON schema:
  {
    "stage": "long_context",
    "model_id": str,
    "target_tokens": int,
    "runs": [
      {"n_gpu_layers": str, "load_ms_manual": int, "load_ms_event": int|None,
       "gen_latency_s": float, "tokens_out": int, "tokens_per_s": float,
       "error": str|None, "wall_s": float,
       "p50_decode_ms": float|None, "p95_decode_ms": float|None,
       "mean_decode_ms": float|None, "sample_count": int|None}
    ],
    "timestamp": float
  }

Note:
  tokens_out approximates word count (split on whitespace) for relative TPS.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
import statistics

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:  # ensure root for 'core' imports
  sys.path.insert(0, str(_ROOT))

from core.config import get_config  # noqa: E402
from core.llm.factory import get_model, clear_provider_cache  # noqa: E402
from core.registry.loader import clear_manifest_cache  # noqa: E402
from core.events import on, reset_listeners_for_tests  # noqa: E402


def _parse_layers(raw: str | None) -> list[str]:
  if not raw:
    return ["0", "6", "12", "auto"]
  return [p.strip() for p in raw.split(",") if p.strip()]


def _collect_load_ms(
  events: List[tuple[str, dict]], model_id: str
) -> int | None:
  for name, payload in events:
    if name == "ModelLoaded" and payload.get("model_id") == model_id:
      return payload.get("load_ms")
  return None


def main() -> int:
  os.environ.setdefault("MIA_LLAMA_FAKE", "0")
  target_tokens = int(os.getenv("MIA_LONG_TOKENS", "512"))
  layer_configs = _parse_layers(os.getenv("MIA_LONG_LAYERS"))

  cfg = get_config()  # initial config
  model_id = cfg.llm.primary.id

  runs: List[Dict[str, Any]] = []
  original_layers_env = os.environ.get("MIA__LLM__PRIMARY__N_GPU_LAYERS")
  try:
    for layers in layer_configs:
      os.environ["MIA__LLM__PRIMARY__N_GPU_LAYERS"] = layers
      clear_manifest_cache()
      clear_provider_cache()

      events: List[tuple[str, dict]] = []
      on(lambda n, p: events.append((n, p)))

      start_wall = time.time()
      error: str | None = None
      manual_load_ms = -1
      event_load_ms: int | None = None
      gen_latency_s = -1.0
      tokens_out = 0
      tokens_per_s = 0.0
      try:
        prov = get_model(model_id)
        t0 = time.time()
        prov.load()
        manual_load_ms = int((time.time() - t0) * 1000)
        event_load_ms = _collect_load_ms(events, model_id)
        gen_t0 = time.time()
        latency_mode = os.getenv("MIA_PERF_LATENCY_DIST", "0") == "1"
        decode_ts: list[float] = []
        prompt_text = (
          "Summarize why deterministic configuration improves "
          "reliability in AI systems."
        )
        if latency_mode and hasattr(prov, "stream"):
          acc: list[str] = []
          for chunk in prov.stream(
            prompt_text,
            max_tokens=target_tokens,
          ):
            if chunk:
              acc.append(chunk)
              decode_ts.append(time.time())
          out = "".join(acc)
        else:
          out = prov.generate(
            prompt_text,
            max_tokens=target_tokens,
          )
        gen_latency_s = time.time() - gen_t0
        tokens_out = len(out.split())
        if gen_latency_s > 0:
          tokens_per_s = tokens_out / gen_latency_s
        p50_decode_ms = p95_decode_ms = mean_decode_ms = None
        sample_count: int | None = None
        if decode_ts:
          deltas = [
            (decode_ts[i] - decode_ts[i - 1]) * 1000
            for i in range(1, len(decode_ts))
          ]
          if deltas:
            d_sorted = sorted(deltas)
            sample_count = len(d_sorted)

            def _pct(arr: list[float], q: float) -> float:
              if not arr:
                return 0.0
              idx = int((q / 100.0) * (len(arr) - 1))
              return arr[idx]

            p50_decode_ms = round(_pct(d_sorted, 50), 2)
            p95_decode_ms = round(_pct(d_sorted, 95), 2)
            mean_decode_ms = round(statistics.fmean(d_sorted), 2)
      except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}".strip()
        p50_decode_ms = p95_decode_ms = mean_decode_ms = None
        sample_count = None
      finally:
        reset_listeners_for_tests()

      runs.append(
        {
          "n_gpu_layers": layers,
          "load_ms_manual": manual_load_ms,
          "load_ms_event": event_load_ms,
          "gen_latency_s": gen_latency_s,
          "tokens_out": tokens_out,
          "tokens_per_s": round(tokens_per_s, 2),
          "error": error,
          "wall_s": round(time.time() - start_wall, 3),
          "p50_decode_ms": p50_decode_ms,
          "p95_decode_ms": p95_decode_ms,
          "mean_decode_ms": mean_decode_ms,
          "sample_count": sample_count,
        }
      )
  finally:
    if original_layers_env is not None:
      os.environ["MIA__LLM__PRIMARY__N_GPU_LAYERS"] = original_layers_env

  report = {
    "stage": "long_context",
    "model_id": model_id,
    "target_tokens": target_tokens,
    "runs": runs,
    "timestamp": time.time(),
  }
  out_path = Path(os.getenv("MIA_PERF_OUT", "reports/perf_long_context.json"))
  out_path.parent.mkdir(parents=True, exist_ok=True)
  out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
  print(json.dumps(report, indent=2))  # noqa: T201
  return 0


if __name__ == "__main__":  # pragma: no cover
  raise SystemExit(main())
