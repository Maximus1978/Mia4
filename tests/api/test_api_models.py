import os
from pathlib import Path
from fastapi.testclient import TestClient
from mia4.api.app import app
from core.registry.loader import clear_manifest_cache, compute_sha256


def _write_manifest(root: Path, model_id: str = "test-model"):
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
            "family: dummy\n"
            "role: primary\n"
            f"path: models/{model_id}.bin\n"
            "context_length: 2048\n"
            "capabilities: [chat]\n"
            f"checksum_sha256: {checksum}\n"
        ),
        encoding="utf-8",
    )
    clear_manifest_cache()


def test_models_list(tmp_path, monkeypatch):
    # Ensure we operate in temp root by chdir then restore.
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        _write_manifest(tmp_path)
        client = TestClient(app)
        r = client.get("/models")
        assert r.status_code == 200
        data = r.json()
        ids = [m["id"] for m in data["models"]]
        assert "test-model" in ids
    finally:
        os.chdir(cwd)
