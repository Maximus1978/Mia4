import json
import time
import sys
from pathlib import Path

# Compare two model manifests (short & long prompt throughput).
# Usage:
#   .venv\Scripts\python.exe scripts\compare_models.py q4km mxfp4

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.llm.factory import get_model, clear_provider_cache  # noqa: E402
from core.registry.loader import clear_manifest_cache  # noqa: E402

PROMPT = (
    "Explain briefly the benefits of attention mechanisms in transformers."
)  # small prompt
LONG_PROMPT = PROMPT + "\n" + ("Performance and scaling considerations. " * 20)


def run_once(model_id: str, max_tokens: int = 64) -> dict:
    clear_manifest_cache()
    clear_provider_cache()
    prov = get_model(model_id)
    t0 = time.time()
    prov.load()
    load_ms = int((time.time() - t0) * 1000)
    g0 = time.time()
    out = prov.generate(PROMPT, max_tokens=max_tokens)
    g1 = time.time()
    toks_short = len(out.split())
    tps_short = toks_short / (g1 - g0) if g1 > g0 else 0
    # long
    g2 = time.time()
    out2 = prov.generate(LONG_PROMPT, max_tokens=max_tokens)
    g3 = time.time()
    toks_long = len(out2.split())
    tps_long = toks_long / (g3 - g2) if g3 > g2 else 0
    return {
        "model_id": model_id,
        "load_ms": load_ms,
        "short_tokens": toks_short,
        "short_tps": round(tps_short, 3),
        "long_tokens": toks_long,
        "long_tps": round(tps_long, 3),
    }


def main():
    if len(sys.argv) < 3:
        print("usage: compare_models.py id1 id2 [out_json]")
        sys.exit(1)
    id1, id2 = sys.argv[1], sys.argv[2]
    out_file = (
        sys.argv[3] if len(sys.argv) > 3 else "reports/compare_models.json"
    )
    res1 = run_once(id1)
    res2 = run_once(id2)
    # Decide better: prioritize long_tps then short_tps
    better = max([res1, res2], key=lambda r: (r["long_tps"], r["short_tps"]))
    report = {
        "results": [res1, res2],
        "better": better["model_id"],
        "timestamp": time.time(),
    }
    Path(out_file).parent.mkdir(parents=True, exist_ok=True)
    Path(out_file).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

 
if __name__ == "__main__":  # pragma: no cover
    main()
