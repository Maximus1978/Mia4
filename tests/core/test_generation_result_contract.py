from core.llm.factory import get_model, clear_provider_cache
from core.registry.loader import clear_manifest_cache, compute_sha256
from pathlib import Path
import textwrap


def _make_manifest(tmp_path: Path, fname: str):
    model_file = tmp_path / "models" / fname
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_bytes(b"dummy")
    checksum = compute_sha256(model_file)
    manifest_text = textwrap.dedent(
        f"""
        id: gen-contract-model
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
    (reg_dir / "gen-contract-model.yaml").write_text(manifest_text, encoding="utf-8")


def test_generation_result_contract(tmp_path: Path):
    _make_manifest(tmp_path, "primary.gguf")
    clear_manifest_cache()
    clear_provider_cache()
    prov = get_model("gen-contract-model", repo_root=tmp_path)
    # Fallback: if generate_result absent, use generate
    if hasattr(prov, "generate_result"):
        res = prov.generate_result("hello world", max_tokens=5)
    else:
        res = prov.generate("hello world", max_tokens=5)
    assert res.version == 2
    assert res.status in ("ok", "error")
    assert res.text
    assert res.usage.prompt_tokens > 0
    assert res.usage.completion_tokens > 0
    assert res.timings.total_ms >= 0
    assert res.model_id == "gen-contract-model"
