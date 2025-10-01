import re
from typing import List

import pytest
from fastapi.testclient import TestClient

import os
from pathlib import Path
from core.config import reset_for_tests
from core.registry.loader import clear_manifest_cache, compute_sha256
from mia4.api.app import app

FUSED_RE = re.compile(r'^(?:assistant\s*final){1,3}', re.IGNORECASE)


@pytest.fixture(autouse=True)
def _reset():
    reset_for_tests()
    yield


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


def _setup_env(tmp_path: Path, model_id: str):
    clear_manifest_cache()
    _prep_manifest(tmp_path, model_id)
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            f"    id: {model_id}\n"
            "    temperature: 0.1\n"
            "    top_p: 0.9\n"
            "    max_output_tokens: 32\n"
            "    n_gpu_layers: 0\n"
            "  skip_checksum: true\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)
    # Force stub provider to avoid real model weight loading.
    os.environ["MIA_FORCE_STUB"] = "1"


def _start_stream(
    client: TestClient, model: str, prompt: str = "hi"
) -> List[str]:
    # Updated API uses POST /generate with JSON body (session_id required).
    payload = {"session_id": "s1", "model": model, "prompt": prompt}
    finals: List[str] = []
    with client.stream(
        "POST", "/generate", json=payload
    ) as r:  # type: ignore[attr-defined]
        current_event = None
        for raw in r.iter_lines():  # type: ignore[attr-defined]
            if not raw:
                continue
            line = raw.strip()
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
                continue
            if line.startswith("data:"):
                payload_line = line[5:].strip()
                if current_event == "final":
                    finals.append(payload_line)
                if current_event == "end":
                    break
    return finals


def test_final_not_starting_with_fused_prefix(tmp_path):
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        model_id = "modelFused"
        _setup_env(tmp_path, model_id)
        client = TestClient(app)
        finals = _start_stream(client, model_id, "Test fused prefix guard")
    finally:
        os.chdir(cwd)
    assert finals, "No final frames captured"
    # Basic JSON assert and prefix check (string form to avoid json noise)
    for f in finals:
        # Extract final text naive (avoid full json parse for speed)
        # Expect pattern '"text": "..."'
        m = re.search(r'"text"\s*:\s*"(.*?)"', f)
        if not m:
            continue
        text = m.group(1)
        assert not FUSED_RE.match(text), f"Fused prefix leaked: {text[:40]}"
        assert '<|channel|>' not in text
        assert '<|start|>' not in text
