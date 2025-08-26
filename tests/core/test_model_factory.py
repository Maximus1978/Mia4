from pathlib import Path
import textwrap

from core.llm.factory import get_model, clear_provider_cache
from core.registry.loader import clear_manifest_cache, compute_sha256
from core.llm import ModelLoadError


def _write(p: Path, content: bytes):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)


def _write_manifest(reg_dir: Path, text: str):
    reg_dir.mkdir(parents=True, exist_ok=True)
    (reg_dir / "dummy.yaml").write_text(text, encoding="utf-8")


def test_factory_get_model_success(tmp_path: Path):
    model_file = tmp_path / "models" / "dummy.bin"
    _write(model_file, b"hello")
    checksum = compute_sha256(model_file)
    manifest_text = textwrap.dedent(f"""
    id: dummy
    family: dummy
    role: primary
    path: {model_file.relative_to(tmp_path)}
    context_length: 32
    capabilities: [chat]
    checksum_sha256: {checksum}
    """)
    _write_manifest(tmp_path / "llm" / "registry", manifest_text)
    clear_manifest_cache()
    clear_provider_cache()
    provider = get_model("dummy", repo_root=tmp_path)
    res = provider.generate("test")
    assert "test" in res.text.lower()


def test_factory_unknown_model(tmp_path: Path):
    clear_manifest_cache()
    clear_provider_cache()
    try:
        get_model("nope", repo_root=tmp_path)
        assert False, "Expected ModelLoadError"
    except ModelLoadError:
        pass


def test_factory_checksum_mismatch(tmp_path: Path):
    model_file = tmp_path / "models" / "dummy.bin"
    _write(model_file, b"data")
    good_checksum = compute_sha256(model_file)
    bad_checksum = ("0" * len(good_checksum))
    manifest_text = textwrap.dedent(f"""
    id: dummy
    family: dummy
    role: primary
    path: {model_file.relative_to(tmp_path)}
    context_length: 32
    capabilities: [chat]
    checksum_sha256: {bad_checksum}
    """)
    _write_manifest(tmp_path / "llm" / "registry", manifest_text)
    clear_manifest_cache()
    clear_provider_cache()
    try:
        get_model("dummy", repo_root=tmp_path)
        assert False, "Expected ModelLoadError due to checksum mismatch"
    except ModelLoadError:
        pass
