from pathlib import Path
import textwrap

from core.llm.factory import (
    get_model,
    get_model_by_role,
    clear_provider_cache,
)
from core.registry.loader import clear_manifest_cache, compute_sha256


def _write(p: Path, content: bytes):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)


def test_get_model_by_role_primary_and_judge(tmp_path: Path):
    # prepare single weights file
    model_file = (
        tmp_path
        / "models"
        / "gpt-oss-20b-GGUF"
        / "gpt-oss-20b-MXFP4.gguf"
    )
    _write(model_file, b"weights")
    checksum = compute_sha256(model_file)
    reg_dir = tmp_path / "llm" / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    # primary manifest
    primary_manifest = textwrap.dedent(f"""
    id: gpt-oss-20b-mxfp4
    family: gpt-oss
    role: primary
    path: {model_file.relative_to(tmp_path)}
    context_length: 1024
    capabilities: [chat]
    checksum_sha256: {checksum}
    """
    )
    # judge manifest referencing same file
    judge_manifest = primary_manifest.replace(
        "role: primary", "role: judge"
    ).replace(
        "gpt-oss-20b-mxfp4", "gpt-oss-20b-mxfp4-judge", 1
    )
    (reg_dir / "primary.yaml").write_text(primary_manifest, encoding="utf-8")
    (reg_dir / "judge.yaml").write_text(judge_manifest, encoding="utf-8")

    clear_manifest_cache()
    clear_provider_cache()

    # By id
    p = get_model("gpt-oss-20b-mxfp4", repo_root=tmp_path)
    assert p.info().role == "primary"
    # By role judge
    j = get_model_by_role("judge", repo_root=tmp_path)
    assert j.info().role == "judge"
    # Unknown role fallback → primary
    x = get_model_by_role("nonexistent_role", repo_root=tmp_path)
    assert x.info().role == "primary"
