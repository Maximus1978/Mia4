import os
import time
from pathlib import Path
import textwrap

from core.llm.factory import get_model, clear_provider_cache
from core.registry.loader import clear_manifest_cache, compute_sha256
from core.events import on, reset_listeners_for_tests


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


def test_perf_fake_generation_tokens_per_sec(tmp_path: Path):
    os.environ["MIA_LLAMA_FAKE"] = "1"
    reset_listeners_for_tests()
    _make_manifest(tmp_path, "primary.gguf")
    clear_manifest_cache()
    clear_provider_cache()
    events = []
    on(lambda name, payload: events.append((name, payload)))
    provider = get_model("primary-model", repo_root=tmp_path)
    provider.load()
    prompt = "hello world"  # 2 tokens simplistic split
    target_tokens = 5000
    t0 = time.time()
    res = provider.generate(prompt, max_tokens=target_tokens)
    elapsed = time.time() - t0
    produced = len(res.text.split())
    tokens_per_sec = produced / elapsed if elapsed > 0 else produced
    # Smoke threshold: fake mode should be fast; conservative lower bound
    assert tokens_per_sec > 2000, f"tokens/s too low: {tokens_per_sec}"
    # Events order check
    names = [n for n, _ in events]
    assert names.count("GenerationStarted") == 1
    assert names.count("GenerationCompleted") == 1
    # Latency consistency (compare with measured elapsed)
    gen_completed_payload = next(
        p for n, p in events if n == "GenerationCompleted"
    )
    reported_ms = gen_completed_payload["latency_ms"]
    # Allow 50% deviation due to coarse timing
    assert abs(reported_ms/1000 - elapsed) < elapsed * 0.5 + 0.01
