import time
from pathlib import Path
import textwrap

from core.llm.factory import get_model, clear_provider_cache, sweep_idle
from core.registry.loader import clear_manifest_cache, compute_sha256
from core.events import on, reset_listeners_for_tests


def test_idle_sweep_unloads_and_emits(tmp_path: Path):
    # prepare model file & manifest
    model_file = tmp_path / "models" / "dummy.bin"
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_bytes(b"hello")
    checksum = compute_sha256(model_file)
    manifest_text = textwrap.dedent(
        f"""
        id: idle-dummy
        family: dummy
        role: primary
        path: {model_file.relative_to(tmp_path)}
        context_length: 32
        capabilities: [chat]
        checksum_sha256: {checksum}
        """
    )
    reg_dir = tmp_path / "llm" / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    (reg_dir / "idle.yaml").write_text(manifest_text, encoding="utf-8")
    clear_manifest_cache()
    clear_provider_cache()

    events = []
    on(lambda n, p: events.append((n, p)))

    prov = get_model("idle-dummy", repo_root=tmp_path)
    prov.generate("hi")
    # simulate old last_used
    prov.last_used = time.time() - 999
    unloaded = sweep_idle({"idle-dummy": 100})
    assert unloaded == [("idle-dummy", "idle")]
    names = [n for n, _ in events]
    assert "ModelUnloaded" in names
    reset_listeners_for_tests()
