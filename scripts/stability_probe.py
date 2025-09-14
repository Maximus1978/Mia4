"""Stability probe: run N sequential generations (primary + lightweight).

Collects latency, decode_tps, output token counts, reasoning ratio.

Usage example:
    python -m scripts.stability_probe --runs 3 \
        --prompt "Test prompt" --host 127.0.0.1 --port 8000

Assumes server already running.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import http.client


def _post_json(host: str, port: int, path: str, payload: dict) -> str:
    conn = http.client.HTTPConnection(host, port, timeout=180)
    body = json.dumps(payload)
    headers = {"Content-Type": "application/json"}
    conn.request("POST", path, body=body, headers=headers)
    resp = conn.getresponse()
    if resp.status != 200:
        raise RuntimeError(f"HTTP {resp.status}: {resp.read()[:200]!r}")
    # Manual SSE read: collect frames until 'end' event
    buf = resp.read().decode("utf-8", errors="ignore")
    return buf


def _parse_usage_frames(raw: str):
    usage = None
    # First token latency not embedded; can be added in future if needed.
    for frame in raw.split("\n\n"):
        if not frame.strip():
            continue
        lines = frame.split("\n")
        evt = None
        data_lines = []
        for ln in lines:
            if ln.startswith("event:"):
                evt = ln.split(":", 1)[1].strip()
            elif ln.startswith("data:"):
                data_lines.append(ln.split(":", 1)[1].strip())
        if not evt:
            continue
        if evt == "usage":
            try:
                usage = json.loads("\n".join(data_lines))
            except Exception:  # noqa: BLE001
                pass
    return usage


def run_probe(host: str, port: int, model: str, prompt: str, runs: int):
    results = []
    for i in range(runs):
        t0 = time.time()
        raw = _post_json(
            host,
            port,
            "/generate",
            {
                "session_id": "stability",
                "model": model,
                "prompt": prompt,
                "overrides": {"reasoning_preset": "low"},
            },
        )
        wall = (time.time() - t0) * 1000.0
        usage = _parse_usage_frames(raw)
        if not usage:
            print(f"Run {i+1}: no usage frame parsed", file=sys.stderr)
            continue
        results.append({
            "run": i+1,
            "wall_ms": wall,
            "latency_ms": usage.get("latency_ms"),
            "decode_tps": usage.get("decode_tps"),
            "output_tokens": usage.get("output_tokens"),
            "reasoning_ratio": usage.get("reasoning_ratio"),
        })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--prompt", default="Explain test architecture briefly.")
    ap.add_argument("--primary_model", default="gpt-oss-20b-mxfp4")
    ap.add_argument("--light_model", default="phi-3.5-mini-instruct-q3_k_s")
    args = ap.parse_args()

    print("== Primary model probe ==")
    primary = run_probe(
        args.host, args.port, args.primary_model, args.prompt, args.runs
    )
    print(json.dumps(primary, indent=2))
    print("== Lightweight model probe ==")
    light = run_probe(
        args.host, args.port, args.light_model, args.prompt, args.runs
    )
    print(json.dumps(light, indent=2))

    # Simple summary
    def _avg(lst, key):
        vals = [x[key] for x in lst if x.get(key) is not None]
        return sum(vals)/len(vals) if vals else None
    summary = {
        "primary_avg_decode_tps": _avg(primary, "decode_tps"),
        "primary_avg_latency_ms": _avg(primary, "latency_ms"),
        "light_avg_decode_tps": _avg(light, "decode_tps"),
        "light_avg_latency_ms": _avg(light, "latency_ms"),
    }
    print("== Summary ==")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
