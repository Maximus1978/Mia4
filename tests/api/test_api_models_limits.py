import os
from pathlib import Path
from fastapi.testclient import TestClient
from mia4.api.app import app
from core.registry.loader import clear_manifest_cache, compute_sha256


def _write_manifest(root: Path, model_id: str = "limit-model"):
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
            "context_length: 1024\n"
            "capabilities: [chat]\n"
            f"checksum_sha256: {checksum}\n"
        ),
        encoding="utf-8",
    )
    # Create a minimal passport file with sampling defaults
    p_dir = root / "models" / model_id
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "passport.yaml").write_text(
        (
            "passport_version: 1\n"
            "hash: 'sha256:stub'\n"
            "sampling_defaults: { max_output_tokens: 64 }\n"
            "reasoning: { default_reasoning_max_tokens: 16 }\n"
        ),
        encoding="utf-8",
    )
    clear_manifest_cache()


def test_models_limits_present(tmp_path):
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        _write_manifest(tmp_path)
        client = TestClient(app)
        r = client.get("/models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data and data["models"], "empty models list"
        item = next(m for m in data["models"] if m["id"] == "limit-model")
        limits = item.get("limits")
        assert limits is not None, "limits missing"
        # Expected keys
        assert "max_output_tokens" in limits
        assert "context_length" in limits
        assert "reasoning_max_tokens" in limits
        # Types/values
        assert limits["context_length"] == 1024
        assert limits["max_output_tokens"] == 64
        assert limits["reasoning_max_tokens"] == 16
    finally:
        os.chdir(cwd)
