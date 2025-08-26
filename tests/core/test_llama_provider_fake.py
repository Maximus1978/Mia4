import os
from pathlib import Path
import textwrap

from core.llm.factory import get_model, clear_provider_cache
from core.registry.loader import clear_manifest_cache, compute_sha256


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


def test_llama_fake_generate_20_tokens(tmp_path: Path):
    os.environ["MIA_LLAMA_FAKE"] = "1"
    _make_manifest(tmp_path, "primary.gguf")
    clear_manifest_cache()
    clear_provider_cache()
    provider = get_model("primary-model", repo_root=tmp_path)
    res = provider.generate("hello world", max_tokens=20)
    assert len(res.text.split()) >= 20


def test_llama_fake_stream_cancel(tmp_path: Path):
    os.environ["MIA_LLAMA_FAKE"] = "1"
    _make_manifest(tmp_path, "primary.gguf")
    clear_manifest_cache()
    clear_provider_cache()
    provider = get_model("primary-model", repo_root=tmp_path)
    collected = []
    for i, chunk in enumerate(provider.stream("hello world", max_tokens=50)):
        collected.append(chunk)
        if i == 5:
            cancel = getattr(provider, "cancel", None)
            if cancel:
                cancel()
    assert 2 <= len(collected) <= 15
