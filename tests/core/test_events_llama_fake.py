import os
from pathlib import Path
import textwrap

from core.llm.factory import get_model, clear_provider_cache
from core.registry.loader import clear_manifest_cache, compute_sha256
from core.events import on


def _write(p: Path, content: bytes):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)


def _make_manifest(tmp_path: Path, fname: str) -> None:
    model_file = tmp_path / "models" / fname
    _write(model_file, b"dummy")
    checksum = compute_sha256(model_file)
    manifest_text = textwrap.dedent(
        f"""
        id: primary-model
        family: qwen
        role: primary
        path: {model_file.relative_to(tmp_path)}
        context_length: 2048
        capabilities: [chat]
        checksum_sha256: {checksum}
        """
    )
    reg_dir = tmp_path / "llm" / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = reg_dir / "primary-model.yaml"
    manifest_file.write_text(manifest_text, encoding="utf-8")


def test_events_emit_for_fake_generation(tmp_path: Path):
    os.environ["MIA_LLAMA_FAKE"] = "1"
    _make_manifest(tmp_path, "primary.gguf")
    clear_manifest_cache()
    clear_provider_cache()
    captured = []
    on(lambda name, payload: captured.append((name, payload)))
    provider = get_model("primary-model", repo_root=tmp_path)
    # load triggers ModelLoaded
    provider.load()
    res = provider.generate("hello world", max_tokens=10)
    assert res.text
    names = [n for n, _ in captured]
    assert "ModelLoaded" in names
    assert "GenerationStarted" in names
    assert "GenerationCompleted" in names
