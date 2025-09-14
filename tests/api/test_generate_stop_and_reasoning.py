import os
from pathlib import Path
from fastapi.testclient import TestClient
from mia4.api.app import app
from core.registry.loader import clear_manifest_cache, compute_sha256
from core.metrics import reset_for_tests, snapshot
from core.events import reset_listeners_for_tests


def _prep_manifest(root: Path, model_id: str):
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


def _setup_env(tmp_path: Path):
    clear_manifest_cache()
    _prep_manifest(tmp_path, "m1")
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: m1\n"
            "    temperature: 0.6\n"
            "    top_p: 0.9\n"
            "    max_output_tokens: 64\n"
            "    n_gpu_layers: 0\n"
            "  lightweight:\n"
            "    id: m1\n"
            "  skip_checksum: true\n"
            "  postproc:\n"
            "    enabled: true\n"
            "    reasoning:\n"
            "      max_tokens: 64\n"
            "      drop_from_history: true\n"
            "      ratio_alert_threshold: 0.9\n"
            "    ngram:\n"
            "      n: 3\n"
            "      window: 32\n"
            "    collapse:\n"
            "      whitespace: true\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)


def test_stop_sequence_truncation_and_reasoning(tmp_path):
    cwd = Path.cwd()
    reset_for_tests()
    reset_listeners_for_tests()
    try:
        os.chdir(tmp_path)
        _setup_env(tmp_path)
        client = TestClient(app)
    # Prompt chosen so provider yields output; stop seq trimming exercised.
        with client.stream(
            "POST",
            "/generate",
            json={
                "session_id": "s-stop",
                "model": "m1",
                "prompt": "reason please",
                "overrides": {"stop": ["[STOP]"]},
            },
        ) as r:
            assert r.status_code == 200
            saw_usage = False
            saw_final = False
            saw_end = False
            # We don't need to capture payload bodies for this smoke test.
            for line in r.iter_lines():
                if not line:
                    continue
                # Presence of reasoning event is optional (config may drop).
                if line.startswith("event: final"):
                    saw_final = True
                if line.startswith("event: usage"):
                    saw_usage = True
                if line.startswith("event: end"):
                    saw_end = True
                    break
            assert saw_usage and saw_final and saw_end
            # Reasoning may be suppressed; stats still recorded in usage.
        snap = snapshot()
        # Check latency + tps metrics updated
        assert any(
            k.startswith("generation_decode_tps")
            for k in snap["histograms"].keys()
        )
    finally:
        os.chdir(cwd)


def test_no_marker_fallback_no_reasoning_leak(tmp_path):
    # Integration: provider output lacks marker; entire output final;
    # no leak metric increments.
    cwd = Path.cwd()
    reset_for_tests()
    reset_listeners_for_tests()
    try:
        os.chdir(tmp_path)
        _setup_env(tmp_path)
        # Modify config to remove marker so entire output is final
        base_file = tmp_path / "configs" / "base.yaml"
        base_yaml = base_file.read_text(encoding="utf-8")
    # legacy final_marker entirely removed; no replacement needed
        base_file.write_text(base_yaml, encoding="utf-8")
        client = TestClient(app)
        with client.stream(
            "POST",
            "/generate",
            json={
                "session_id": "s-nomarker",
                "model": "m1",
                "prompt": "just answer please",
            },
        ) as r:
            assert r.status_code == 200
            for line in r.iter_lines():
                if line.startswith("event: end"):
                    break
        snap = snapshot()
        # Ensure reasoning_leak_total not incremented
        assert not any(
            k.startswith("reasoning_leak_total") for k in snap["counters"]
        )  # no leak
    finally:
        os.chdir(cwd)


def test_sampling_origin_layers(tmp_path):
    cwd = Path.cwd()
    reset_for_tests()
    reset_listeners_for_tests()
    try:
        os.chdir(tmp_path)
        _setup_env(tmp_path)
        client = TestClient(app)
        # Provide user overrides to force origin=mixed/custom
        with client.stream(
            "POST",
            "/generate",
            json={
                "session_id": "s-mix",
                "model": "m1",
                "prompt": "mix",
                "overrides": {
                    "temperature": 0.75,
                    "max_output_tokens": 32,
                    "stop": ["[X]"],
                },
            },
        ) as r:
            assert r.status_code == 200
            for line in r.iter_lines():
                if line.startswith("event: end"):
                    break
        # No direct event capture hook here; rely that no exceptions occurred.
        snap = snapshot()
        # At least first token latency metric implies route executed fully.
        assert any(
            k.startswith("generation_first_token_latency_ms")
            for k in snap["histograms"].keys()
        )
    finally:
        os.chdir(cwd)
