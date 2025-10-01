import os
from pathlib import Path
from fastapi.testclient import TestClient
from mia4.api.app import app
from core.registry.loader import clear_manifest_cache, compute_sha256


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
            "    max_output_tokens: 32\n"
            "    n_gpu_layers: 0\n"
            "  skip_checksum: true\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)


def test_final_frame_sanitized(tmp_path):
    # Smoke contract: ensure we see event: final and it has no service markers.
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        _setup_env(tmp_path)
        client = TestClient(app)
        final_payload = None
        with client.stream(
            "POST",
            "/generate",
            json={
                "session_id": "s1",
                "model": "modelA",
                "prompt": "hello",
            },
        ) as r:
            assert r.status_code == 200
            for raw in r.iter_lines():
                if not raw:
                    continue
                if raw.startswith("event: final"):
                    # Next data: line will contain final JSON payload
                    continue
                if raw.startswith("data:"):
                    import json
                    data_str = raw[5:].strip()
                    try:
                        obj = json.loads(data_str)
                    except Exception:  # noqa: BLE001
                        continue
                    if obj.get("text") and obj.get("model_id"):
                        final_payload = obj
                if raw.startswith("event: end"):
                    break
        assert final_payload is not None, "final payload missing"
        assert "<|" not in final_payload["text"], final_payload["text"]
    finally:
        os.chdir(cwd)
