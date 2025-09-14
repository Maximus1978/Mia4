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
            "family: dummy\n"
            "role: primary\n"
            f"path: models/{model_id}.bin\n"
            "context_length: 2048\n"
            "capabilities: [chat]\n"
            f"checksum_sha256: {checksum}\n"
        ),
        encoding="utf-8",
    )


def test_pipeline_hello(tmp_path):
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        clear_manifest_cache()
        _prep_manifest(tmp_path, "modelA")
        # Minimal config enabling llm module (required after postproc changes)
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
                "    max_output_tokens: 16\n"
                "    n_gpu_layers: 0\n"
                "  lightweight:\n"
                "    id: modelA\n"
                "    temperature: 0.4\n"
                "  skip_checksum: true\n"
            ),
            encoding="utf-8",
        )
        os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)
        client = TestClient(app)
        # models list
        r_models = client.get("/models")
        assert r_models.status_code == 200
        assert any(m["id"] == "modelA" for m in r_models.json()["models"])
        # generate simple greeting
        with client.stream(
            "POST",
            "/generate",
            json={"session_id": "s1", "model": "modelA", "prompt": "Привет"},
        ) as r:
            assert r.status_code == 200
            got_token = False
            for line in r.iter_lines():
                if line.startswith("event: token"):
                    got_token = True
                    break
            assert got_token, "no token from pipeline"
    finally:
        os.chdir(cwd)
