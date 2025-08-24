import json
import time
import os
import pathlib
import sys
from statistics import median

# Ensure project root on path before importing project modules
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config.loader import get_config, clear_config_cache  # noqa: E402
from core.llm.factory import get_model, clear_provider_cache  # noqa: E402

# Probe scenarios (short output). Long scenario executed separately
# for latency ratio measurement.
SHORT_SCENARIOS = [
    {"name": "short_cpu", "env": {"MIA__LLM__PRIMARY__N_GPU_LAYERS": "0"}},
    {"name": "short_gpu6", "env": {"MIA__LLM__PRIMARY__N_GPU_LAYERS": "6"}},
]

LONG_TARGET_TOKENS = int(os.getenv("MIA_PROBE_LONG_TOKENS", "512"))
SHORT_TARGET_TOKENS = int(os.getenv("MIA_PROBE_SHORT_TOKENS", "64"))

OUT_PATH = pathlib.Path("reports/perf_probe.json")


def run_short_scenario(s, max_tokens: int):
    for k, v in s["env"].items():
        os.environ[k] = v
    clear_config_cache()
    cfg = get_config()
    clear_provider_cache()
    provider = get_model(cfg.llm.primary.id, skip_checksum=True)
    prompt = "Short perf probe."
    t0 = time.time()
    out = provider.generate(prompt, max_tokens=max_tokens)
    dt = time.time() - t0
    tokens_out = len(out.split())
    tps = tokens_out / dt if dt > 0 else None
    return {
        "scenario": s["name"],
        "mode": "short",
        "tokens_out": tokens_out,
        "latency_s": round(dt, 3),
        "tps": round(tps, 3) if tps else None,
    }


def measure_latency_stream(n_gpu_layers: str | int, max_tokens: int):
    os.environ["MIA__LLM__PRIMARY__N_GPU_LAYERS"] = str(n_gpu_layers)
    clear_config_cache()
    cfg = get_config()
    clear_provider_cache()
    provider = get_model(cfg.llm.primary.id, skip_checksum=True)
    prompt = "Long perf probe latency stream." * 4
    ts = []
    t0 = time.time()
    for chunk in provider.stream(prompt, max_tokens=max_tokens):
        if chunk:
            ts.append(time.time())
    total = time.time() - t0
    tokens_out = len(" ".join(["X" for _ in ts]).split())  # approx by chunks
    if len(ts) > 1:
        dts = [(ts[i] - ts[i - 1]) * 1000 for i in range(1, len(ts))]
        p50 = median(dts)
        dts_sorted = sorted(dts)
        p95 = dts_sorted[int(0.95 * (len(dts_sorted) - 1))]
    else:
        p50 = p95 = None
    tps = tokens_out / total if total > 0 else None
    return {
        "scenario": f"long_gpu{n_gpu_layers}",
        "mode": "long",
        "tokens_out": tokens_out,
        "latency_s": round(total, 3),
        "tps": round(tps, 3) if tps else None,
        "p50_decode_ms": round(p50, 2) if p50 else None,
        "p95_decode_ms": round(p95, 2) if p95 else None,
    }


def main():
    # Short scenarios
    short_results = [
        run_short_scenario(s, SHORT_TARGET_TOKENS) for s in SHORT_SCENARIOS
    ]
    # Long latency (single GPU mode from env or default 6)
    long_gpu_layers = os.getenv("MIA_PROBE_LONG_GPU_LAYERS", "6")
    long_result = measure_latency_stream(long_gpu_layers, LONG_TARGET_TOKENS)
    results = short_results + [long_result]

    prev = {}
    if OUT_PATH.exists():
        try:
            prev_json = json.loads(OUT_PATH.read_text())
            prev = {r["scenario"]: r for r in prev_json.get("results", [])}
        except Exception:  # noqa: BLE001
            prev = {}
    cfg = get_config()
    thresholds = cfg.perf.thresholds if cfg.perf else None
    tps_thresh = thresholds.tps_regression_pct if thresholds else 0.15
    p95_thresh = thresholds.p95_regression_pct if thresholds else 0.20
    ratio_limit = thresholds.p95_ratio_limit if thresholds else 1.30
    ratio_reg_thresh = (
        thresholds.p95_ratio_regression_pct if thresholds else 0.20
    )

    regressions: list[str] = []
    issues: list[str] = []

    # Throughput regressions (short scenarios)
    for r in short_results:
        old = prev.get(r["scenario"])
        if old and old.get("tps") and r.get("tps"):
            if (old["tps"] - r["tps"]) / old["tps"] > tps_thresh:
                r["regression_tps"] = True
                regressions.append(r["scenario"])

    # p95 latency regression (long scenario only if previous exists with p95)
    long_old = prev.get(long_result["scenario"]) if long_result else None
    if (
        long_old
        and long_old.get("p95_decode_ms")
        and long_result.get("p95_decode_ms")
    ):
        if (
            (long_result["p95_decode_ms"] - long_old["p95_decode_ms"])
            / long_old["p95_decode_ms"]
            > p95_thresh
        ):
            long_result["regression_p95"] = True
            regressions.append(long_result["scenario"])

    # Derive ratios if we have a matching short scenario (prefer gpu6 ref)
    ref_short = next(
        (r for r in short_results if r["scenario"] == "short_gpu6"),
        short_results[0],
    )
    if ref_short.get("p95_decode_ms") and long_result.get("p95_decode_ms"):
        ratio = long_result["p95_decode_ms"] / ref_short["p95_decode_ms"]
        long_result["p95_ratio"] = round(ratio, 3)
        if ratio > ratio_limit:
            long_result["sla_violation_p95_ratio"] = True
            issues.append("p95_ratio_limit")
        # Compare with previous ratio
        if long_old and long_old.get("p95_ratio"):
            prev_ratio = long_old["p95_ratio"]
            if (
                prev_ratio
                and (ratio - prev_ratio) / prev_ratio > ratio_reg_thresh
            ):
                long_result["regression_p95_ratio"] = True
                regressions.append(long_result["scenario"] + ":p95_ratio")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": time.time(),
        "results": results,
        "regressions": regressions,
        "issues": issues,
        "thresholds": {
            "tps_regression_pct": tps_thresh,
            "p95_regression_pct": p95_thresh,
            "p95_ratio_limit": ratio_limit,
            "p95_ratio_regression_pct": ratio_reg_thresh,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))

 
if __name__ == "__main__":
    main()
