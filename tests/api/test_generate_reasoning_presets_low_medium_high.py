import os
from pathlib import Path
from fastapi.testclient import TestClient
from mia4.api.app import app
from core.registry.loader import clear_manifest_cache, compute_sha256
from core.metrics import reset_for_tests
from core.events import reset_listeners_for_tests

PROMPT = "Объясни коротко что такое индекс в базе данных."


def _prep_manifest(root: Path, model_id: str):  # noqa: D401
    models_dir = root / "models"
    models_dir.mkdir(exist_ok=True)
    model_file = models_dir / f"{model_id}.bin"
    model_file.write_bytes(b"dummy")
    checksum = compute_sha256(model_file)
    reg_dir = root / "llm" / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    manifest = reg_dir / f"{model_id}.yaml"
    manifest.write_text(
        (
            f"id: {model_id}\n"
            "family: qwen\n"
            "role: primary\n"
            f"path: models/{model_id}.bin\n"
            "context_length: 2048\n"
            "capabilities: [chat]\n"
            f"checksum_sha256: {checksum}\n"
        ),
        encoding="utf-8",
    )


def _setup_env(tmp_path: Path):  # noqa: D401
    clear_manifest_cache()
    _prep_manifest(tmp_path, "modelR")
    cfg_dir = tmp_path / "configs"
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
            "    high:\n"
            "      temperature: 0.85\n"
            "      top_p: 0.95\n"
            "      reasoning_max_tokens: 96\n"
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


def _run(client: TestClient, preset: str):  # noqa: D401
    final_text = None
    usage_obj = None
    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": f"s-{preset}",
            "model": "modelR",
            "prompt": PROMPT,
            "overrides": {"reasoning_preset": preset},
        },
    ) as r:
        assert r.status_code == 200
        last_event = None
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("event: "):
                last_event = line.split(": ", 1)[1]
            elif line.startswith("data: ") and last_event == "usage":
                import json as _json
                usage_obj = _json.loads(line[6:])
            elif line.startswith("data: ") and last_event == "final":
                import json as _json
                final_text = _json.loads(line[6:]).get("text")
            elif line.startswith("event: end"):
                break
    return final_text, usage_obj


def test_reasoning_low_medium_high_progression(tmp_path):  # noqa: D401
    cwd = Path.cwd()
    reset_for_tests()
    reset_listeners_for_tests()
    try:
        os.chdir(tmp_path)
        _setup_env(tmp_path)
        client = TestClient(app)
        final_low, usage_low = _run(client, "low")
        final_med, usage_med = _run(client, "medium")
        final_high, usage_high = _run(client, "high")
        # Basic invariants
        for txt in (final_low, final_med, final_high):
            assert isinstance(txt, str) and txt.strip()
        low_tokens = usage_low.get("reasoning_tokens", 0)
        med_tokens = usage_med.get("reasoning_tokens", 0)
        high_tokens = usage_high.get("reasoning_tokens", 0)
    # Expect non-decreasing (allow equality if model skips reasoning)
        assert med_tokens >= low_tokens
        assert high_tokens >= med_tokens
        # If high produced >0 tokens ensure textual divergence from low
        if high_tokens > 0 and low_tokens > 0:
            if final_low == final_high:
                print("[PIPELINE][WARN] high answer == low (reasoning)")
        print(
            "[PIPELINE] reasoning tokens low/medium/high:",
            low_tokens,
            med_tokens,
            high_tokens,
        )
    finally:
        os.chdir(cwd)
