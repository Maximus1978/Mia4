from core.events import reset_listeners_for_tests
from core.llm.factory import get_model, clear_provider_cache
from core.registry.loader import clear_manifest_cache, compute_sha256
from pathlib import Path
import textwrap


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


def test_generation_chunk_sequence_and_final(tmp_path: Path):
    reset_listeners_for_tests()
    _make_manifest(tmp_path, "primary.gguf")
    clear_manifest_cache()
    clear_provider_cache()
    provider = get_model("primary-model", repo_root=tmp_path)
    events: list[tuple[str, dict]] = []
    from core.events import subscribe
    unsubscribe = subscribe(lambda n, p: events.append((n, p)))
    try:
        chunks = list(provider.stream("alpha beta", max_tokens=10))
    finally:
        unsubscribe()
    names = [n for n, _ in events]
    # Allow an initial ModelLoaded (or other preload) event; ensure
    # GenerationStarted exists and precedes chunks.
    assert "GenerationStarted" in names, f"Events: {names}"
    start_idx = names.index("GenerationStarted")
    chunk_events = [p for n, p in events if n == "GenerationChunk"]
    assert len(chunk_events) > 0
    # All chunk events should come after GenerationStarted
    chunk_name_indices = [
        i for i, n in enumerate(names) if n == "GenerationChunk"
    ]
    assert all(i > start_idx for i in chunk_name_indices)
    # seq monotonic
    seqs = [p["seq"] for p in chunk_events]
    assert seqs == list(range(len(seqs)))
    # tokens_out cumulative and equals produced tokens
    tokens_out = [p["tokens_out"] for p in chunk_events]
    assert tokens_out == list(range(1, len(tokens_out) + 1))
    completed = [p for n, p in events if n == "GenerationCompleted"]
    assert len(completed) == 1
    final = completed[0]
    # GenerationCompleted should be last or after last chunk
    last_completed_idx = max(
        i for i, n in enumerate(names) if n == "GenerationCompleted"
    )
    assert last_completed_idx >= chunk_name_indices[-1]
    assert final["output_tokens"] == tokens_out[-1]
    assert final["status"] == "ok"
    assert len(chunks) == tokens_out[-1]  # rough approximation
