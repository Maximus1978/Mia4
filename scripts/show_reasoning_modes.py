"""Utility: print final answers for given prompt in multiple reasoning presets.

Usage (one line):
    python scripts/show_reasoning_modes.py --prompt "..." --modes off medium
"""
from __future__ import annotations

import argparse
import json
import os
import uuid

from fastapi.testclient import TestClient
from mia4.api.app import app


def stream_final(
    client: TestClient,
    model: str,
    prompt: str,
    preset: str,
    max_tokens: int,
) -> str:
    payload = {
        "session_id": f"s-{preset}-{uuid.uuid4().hex[:6]}",
        "model": model,
        "prompt": prompt,
        "overrides": {
            "reasoning_preset": preset,
            "max_output_tokens": max_tokens,
        },
    }
    with client.stream("POST", "/generate", json=payload) as r:
        if r.status_code != 200:
            return f"<error status={r.status_code}>"
        last = None
        final_text = None
        usage = None
        for ln in r.iter_lines():
            if not ln:
                continue
            if ln.startswith("event: "):
                last = ln.split(": ", 1)[1]
            elif ln.startswith("data: ") and last == "usage":
                try:
                    usage = json.loads(ln[6:])
                except Exception:  # noqa: BLE001
                    pass
            elif ln.startswith("data: ") and last == "final":
                try:
                    final_text = json.loads(ln[6:]).get("text")
                except Exception:  # noqa: BLE001
                    final_text = "<parse-error>"
                break
        if final_text is None:
            final_text = "<no-final>"
        # Truncate for console readability
        trimmed = (
            final_text[:1000] + "…" if len(final_text) > 1000 else final_text
        )
        rtoks = (
            usage.get("reasoning_tokens") if isinstance(usage, dict) else None
        )
        return f"reasoning_tokens={rtoks}\n{trimmed}"  # noqa: E501


def main() -> int:  # noqa: D401
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--model", default="gpt-oss-20b-mxfp4")
    ap.add_argument("--modes", nargs="+", default=["off", "medium"])
    ap.add_argument("--max", type=int, default=512, dest="max_tokens")
    ap.add_argument("--config_dir", default="configs")
    args = ap.parse_args()
    os.environ["MIA_CONFIG_DIR"] = args.config_dir
    client = TestClient(app)
    for mode in args.modes:
        out = stream_final(
            client, args.model, args.prompt, mode, args.max_tokens
        )
        print(f"\n=== {mode.upper()} ===\n{out}")
    return 0


if __name__ == "__main__":  # noqa: D401
    raise SystemExit(main())
