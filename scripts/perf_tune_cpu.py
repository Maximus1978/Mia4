"""CPU tuning sweep for n_threads / n_batch (Step 10.2 helper).

Env overrides:
  MIA_TUNE_THREADS="auto,4,8,16"  ("auto" or empty token -> omit override)
  MIA_TUNE_BATCHES="128,256,512"

Output:
  reports/tune_results.json  (list of measurements)
  Prints markdown table sorted by tokens/s desc.

Note: Uses skip_checksum for speed (assumes prior verified checksum).
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

from core.llm.factory import get_model, clear_provider_cache  # noqa: E402
from core.registry.loader import clear_manifest_cache  # noqa: E402
from core.config.loader import clear_config_cache  # noqa: E402


def _parse_list(env_val: str | None, defaults: list[str]) -> list[str]:
    if not env_val:
        return defaults
    parts = [p.strip() for p in env_val.split(",") if p.strip()]
    return parts or defaults


def main() -> int:
    threads_raw = _parse_list(
        os.getenv("MIA_TUNE_THREADS"),
        ["auto", "4", "8", "16"],
    )
    batches_raw = _parse_list(
        os.getenv("MIA_TUNE_BATCHES"),
        ["128", "256", "512"],
    )
    model_id = os.getenv("MIA_PRIMARY_ID", "gpt-oss-20b-q4km")
    prompt = "List three reasons reproducible configs reduce AI system risk."

    results: list[dict] = []
    for th in threads_raw:
        for nb in batches_raw:
            if th == "auto" or th == "":
                os.environ.pop("MIA__LLM__PRIMARY__N_THREADS", None)
            else:
                os.environ["MIA__LLM__PRIMARY__N_THREADS"] = th
            os.environ["MIA__LLM__PRIMARY__N_BATCH"] = nb
            clear_provider_cache()
            clear_manifest_cache()
            clear_config_cache()
            prov = get_model(model_id, skip_checksum=True)
            t0 = time.time()
            prov.load()
            load_ms = int((time.time() - t0) * 1000)
            g0 = time.time()
            out = prov.generate(prompt, max_tokens=64)
            gen_s = time.time() - g0
            toks = len(out.split())
            tps = toks / gen_s if gen_s > 0 else 0.0
            results.append({
                "n_threads": th,
                "n_batch": nb,
                "load_ms": load_ms,
                "tokens_out": toks,
                "gen_s": round(gen_s, 3),
                "tps": round(tps, 2),
            })

    results.sort(key=lambda r: r["tps"], reverse=True)
    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tune_results.json").write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    headers = [
        "n_threads",
        "n_batch",
        "load_ms",
        "tokens_out",
        "gen_s",
        "tps",
    ]
    print("| " + " | ".join(headers) + " |")  # noqa: T201
    print("| " + " | ".join(["---"] * len(headers)) + " |")  # noqa: T201
    for r in results:
        row = "| " + " | ".join(str(r[h]) for h in headers) + " |"
        print(row)  # noqa: T201
    best = results[0] if results else None
    if best:
        print(
            f"\nBest: n_threads={best['n_threads']} "
            f"n_batch={best['n_batch']} tps={best['tps']}"
        )  # noqa: T201
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
