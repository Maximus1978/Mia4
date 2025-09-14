"""Utility: print two readable answers for reasoning presets off vs low.

Usage (PowerShell):
  python scripts/compare_off_low.py "Ваш вопрос здесь"  # uses existing config
    python scripts/compare_off_low.py --dummy "Ваш вопрос"  # dummy model

When --dummy is used we create a temp config & dummy model manifest so the
script runs without large model weights.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from mia4.api.app import app
from core.registry.loader import clear_manifest_cache, compute_sha256


PROMPT_FALLBACK = (
    "Объясни коротко что такое индекс в базе данных."  # fallback prompt
)


def _prep_dummy_env() -> None:
    """Create a temporary config + dummy model manifest (in-process)."""
    tmp = Path(tempfile.mkdtemp(prefix="mia_off_low_"))
    models_dir = tmp / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_file = models_dir / "modelR.bin"
    model_file.write_bytes(b"dummy")
    checksum = compute_sha256(model_file)
    reg_dir = tmp / "llm" / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    reg_dir.joinpath("modelR.yaml").write_text(
        (
            "id: modelR\n"
            "family: qwen\n"
            "role: primary\n"
            "path: models/modelR.bin\n"
            "context_length: 2048\n"
            "capabilities: [chat]\n"
            f"checksum_sha256: {checksum}\n"
        ),
        encoding="utf-8",
    )
    cfg_dir = tmp / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: modelR\n"
            "    temperature: 0.7\n"
            "    top_p: 0.9\n"
            "    max_output_tokens: 80\n"
            "    n_gpu_layers: 0\n"
            "  lightweight:\n"
            "    id: modelR\n"
            "  reasoning_presets:\n"
            "    low:\n"
            "      temperature: 0.6\n"
            "      top_p: 0.9\n"
            "      reasoning_max_tokens: 16\n"
            "    medium:\n"
            "      temperature: 0.7\n"
            "      top_p: 0.92\n"
            "      reasoning_max_tokens: 48\n"
            "  postproc:\n"
            "    enabled: true\n"
            "    reasoning:\n"
            "      max_tokens: 256\n"
            "      drop_from_history: true\n"
            "      ratio_alert_threshold: 0.9\n"
            "    ngram:\n"
            "      n: 3\n"
            "      window: 64\n"
            "    collapse:\n"
            "      whitespace: true\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)
    clear_manifest_cache()


def fetch_answer(
    client: TestClient, prompt: str, preset: str
) -> tuple[str, dict]:
    final_text = None
    usage_obj: dict | None = None
    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": f"sess-{preset}",
            "model": "modelR",
            "prompt": prompt,
            "overrides": {"reasoning_preset": preset},
        },
    ) as r:
        last_event = None
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("event: "):
                last_event = line.split(": ", 1)[1]
            elif line.startswith("data: ") and last_event == "final":
                final_text = json.loads(line[6:]).get("text")
            elif line.startswith("data: ") and last_event == "usage":
                usage_obj = json.loads(line[6:])
            elif line.startswith("event: end"):
                break
    return final_text or "", usage_obj or {}


def main():  # noqa: D401
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="?", default=PROMPT_FALLBACK)
    ap.add_argument("--dummy", action="store_true", help="Use dummy model env")
    args = ap.parse_args()
    if args.dummy:
        _prep_dummy_env()
    client = TestClient(app)
    off_text, off_usage = fetch_answer(client, args.prompt, "off")
    low_text, low_usage = fetch_answer(client, args.prompt, "low")
    print("===== REASONING PRESET: off =====")
    print(off_text.strip())
    print("-- usage:", json.dumps(off_usage, ensure_ascii=False))
    print()  # spacer
    print("===== REASONING PRESET: low =====")
    print(low_text.strip())
    print("-- usage:", json.dumps(low_usage, ensure_ascii=False))
    if off_text.strip() == low_text.strip():
        print(
            "[NOTE] Answers identical; model may ignore reasoning preset or"
            " presets alias same sampling."
        )


if __name__ == "__main__":  # pragma: no cover
    main()
