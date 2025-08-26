from pathlib import Path
import textwrap

from core.registry.loader import (
    load_manifests,
    verify_model_checksum,
    compute_sha256,
)
from core.registry.manifest import ModelManifest
from core.llm import ModelLoadError


def _write(file: Path, content: str):
    file.write_text(content, encoding="utf-8")


def test_load_manifests_index_and_duplicate_detection(tmp_path: Path):
    reg_dir = tmp_path / "llm" / "registry"
    reg_dir.mkdir(parents=True)
    m1 = textwrap.dedent(
        """
        id: model-a
        family: fam
        role: primary
        path: models/a.gguf
        quant: q4
        context_length: 2048
        capabilities: [chat]
        checksum_sha256: deadbeef
        """
    )
    m2 = m1.replace("model-a", "model-b").replace("deadbeef", "cafebabe")
    _write(reg_dir / "model-a.yaml", m1)
    _write(reg_dir / "model-b.yaml", m2)
    idx = load_manifests(tmp_path)
    assert set(idx.keys()) == {"model-a", "model-b"}


def test_verify_checksum_success_and_failure(tmp_path: Path):
    model_file = tmp_path / "models" / "test.bin"
    model_file.parent.mkdir(parents=True)
    model_file.write_bytes(b"hello world")
    checksum = compute_sha256(model_file)
    manifest = ModelManifest(
        id="m1",
        family="fam",
        role="primary",
        path=str(model_file.relative_to(tmp_path)),
        quant=None,
        context_length=1024,
        capabilities=["chat"],
        checksum_sha256=checksum,
    )
    assert verify_model_checksum(manifest, tmp_path)
    model_file.write_bytes(b"changed")
    try:
        verify_model_checksum(manifest, tmp_path)
        assert False, "Expected checksum mismatch"
    except ModelLoadError:
        pass
