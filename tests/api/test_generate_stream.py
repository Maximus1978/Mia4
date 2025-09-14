import os
import time
from pathlib import Path
from fastapi.testclient import TestClient
from mia4.api.app import app
from core.registry.loader import clear_manifest_cache, compute_sha256
from core.metrics import snapshot, reset_for_tests
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
    _prep_manifest(tmp_path, "modelA")
    _prep_manifest(tmp_path, "modelB")
    # Minimal config enabling llm module
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: modelA\n"
            "    temperature: 0.6\n"
            "    top_p: 0.9\n"
            "    max_output_tokens: 64\n"
            "    n_gpu_layers: 0\n"
            "  lightweight:\n"
            "    id: modelA\n"
            "    temperature: 0.4\n"
            "  skip_checksum: true\n"
        ),
        encoding="utf-8",
    )
    # Point loader to this temp config directory
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)


def test_stream_generate_first_token(tmp_path):
    cwd = Path.cwd()
    reset_for_tests()
    reset_listeners_for_tests()
    try:
        os.chdir(tmp_path)
        _setup_env(tmp_path)
        client = TestClient(app)
        t_start = time.time()
        with client.stream(
            "POST",
            "/generate",
            json={
                "session_id": "s1",
                "model": "modelA",
                "prompt": "hello world",
                "overrides": {},
            },
        ) as r:
            assert r.status_code == 200
            got_token = False
            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith("event: token"):
                    got_token = True
                    break
            assert got_token, "No token event received"
            assert (time.time() - t_start) < 1.0
        snap = snapshot()
        assert any(
            k.startswith("generation_first_token_latency_ms")
            for k in snap["histograms"].keys()
        )
    finally:
        os.chdir(cwd)


def test_model_switch(tmp_path):
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        _setup_env(tmp_path)
        client = TestClient(app)
        models = ["modelA", "modelB"]
        used = []
        for mid in models:
            with client.stream(
                "POST",
                "/generate",
                json={
                    "session_id": "s1",
                    "model": mid,
                    "prompt": "ping",
                },
            ) as r:
                assert r.status_code == 200
                for line in r.iter_lines():
                    if line.startswith("event: usage"):
                        used.append(mid)
                        break
        assert used == models
    finally:
        os.chdir(cwd)


def test_decode_tps_positive(tmp_path):
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        _setup_env(tmp_path)
        client = TestClient(app)
        with client.stream(
            "POST",
            "/generate",
            json={
                "session_id": "s3",
                "model": "modelA",
                "prompt": "quick run",
            },
        ) as r:
            assert r.status_code == 200
            for line in r.iter_lines():
                if line.startswith("event: usage"):
                    break
        snap = snapshot()
        assert any(
            k.startswith("generation_decode_tps")
            for k in snap["histograms"].keys()
        )
    finally:
        os.chdir(cwd)


def test_error_on_empty_prompt(tmp_path):
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        _setup_env(tmp_path)
        client = TestClient(app)
        r = client.post(
            "/generate",
            json={
                "session_id": "s3",
                "model": "modelA",
                "prompt": "   ",
            },
        )
        assert r.status_code == 400
    finally:
        os.chdir(cwd)
