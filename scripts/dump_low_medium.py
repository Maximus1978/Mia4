"""Dump readable answers from real model for reasoning presets low vs medium.

Usage (PowerShell):
    $env:MIA_REAL_MODEL="1"; python scripts/dump_low_medium.py "Ваш вопрос"

If no prompt given, uses a default about DB index.
Outputs per preset:
    - Raw final answer text
    - reasoning_tokens / final_tokens / reasoning_ratio / output_tokens

Flags:
    --max-chars N          Truncate printed answer (debug convenience)
    --max-output-tokens N  Override max_output_tokens (default 256)
    --timeout S            generation_timeout_s override (seconds)
    --show-stream          Print streamed token pieces (first 200 chars each)

This script is streaming-aware; it captures usage BEFORE final to make sure
long generations still surface token stats if a timeout fires.
"""
from __future__ import annotations

import argparse
import json
import os
from fastapi.testclient import TestClient
from mia4.api.app import app

DEFAULT_PROMPT = "Что такое индекс в базе данных?"
PRESETS = ["low", "medium"]


def stream_once(
    prompt: str,
    preset: str,
    model_id: str,
    max_output_tokens: int,
    timeout_s: float | None,
    show_stream: bool,
):  # noqa: D401
    final_text: str | None = None
    usage: dict | None = None
    # simple assembly of final text from token events (in case final missing)
    assembled: list[str] = []
    client = TestClient(app)
    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": f"dump-{preset}",
            "model": model_id,
            "prompt": prompt,
            "overrides": {
                "reasoning_preset": preset,
                "max_output_tokens": max_output_tokens,
                **({"generation_timeout_s": timeout_s} if timeout_s else {}),
            },
        },
    ) as r:
        r.raise_for_status()
        last = None
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("event: "):
                last = line.split(": ", 1)[1]
            elif line.startswith("data: "):
                raw = line[6:]
                if last == "final":
                    try:
                        tok = json.loads(raw).get("text", "")
                        if tok:
                            assembled.append(tok)
                            if show_stream:
                                print(f"[tok] {tok[:200]}")
                    except Exception:  # noqa: BLE001
                        pass
                if last == "final":
                    final_text = json.loads(raw).get("text")
                elif last == "usage":
                    usage = json.loads(raw)
            if last == "end":
                break
    if final_text is None:  # fallback to assembled stream
        final_text = "".join(assembled)
    return final_text, usage or {}


def main():  # noqa: D401
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT)
    ap.add_argument(
        "--model",
        default=os.environ.get("MIA_REAL_MODEL_ID", "gpt-oss-20b-mxfp4"),
    )
    ap.add_argument("--max-chars", type=int, default=None)
    ap.add_argument(
        "--max-output-tokens",
        type=int,
        default=256,
        help="Override max_output_tokens (smaller speeds up run)",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="generation_timeout_s override (seconds)",
    )
    ap.add_argument(
        "--show-stream",
        action="store_true",
        help="Print streamed token fragments (debug)",
    )
    args = ap.parse_args()

    for preset in PRESETS:
        text, usage = stream_once(
            args.prompt,
            preset,
            args.model,
            args.max_output_tokens,
            args.timeout,
            args.show_stream,
        )
        if args.max_chars and len(text) > args.max_chars:
            display = text[: args.max_chars] + "... <truncated>"
        else:
            display = text
        print("===== PRESET:", preset, "=====")
        print(display.strip())
        usage_view = {
            k: usage.get(k)
            for k in [
                "reasoning_tokens",
                "final_tokens",
                "reasoning_ratio",
                "output_tokens",
            ]
        }
        print("-- usage:", json.dumps(usage_view, ensure_ascii=False))
        print()


if __name__ == "__main__":  # pragma: no cover
    main()
