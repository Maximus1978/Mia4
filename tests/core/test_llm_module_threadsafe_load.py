import threading
import time

from core.modules.module_manager import LLMModule
from core.config import get_config
from core.llm import DummyProvider


def test_llmmodule_concurrent_load_single_instance():
    cfg = get_config().llm
    primary_id = cfg.primary.id

    # Monkeypatch heavy provider with lightweight fake (no real model load)
    from core.modules import module_manager as mm

    class FakeProvider(DummyProvider):
        def __init__(self, **kw):  # noqa: D401, ANN001
            super().__init__(model_id=kw.get("model_id"), role=kw.get("role"))

    orig = mm.LlamaCppProvider
    mm.LlamaCppProvider = FakeProvider  # type: ignore
    try:
        mod = LLMModule()

        providers = []
        errors = []

        def worker():
            try:
                prov = mod.get_provider(
                    primary_id,
                    repo_root=".",
                    skip_checksum=True,
                )
                providers.append(prov)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        assert not errors, f"Errors during concurrent load: {errors}"
        assert len(providers) == 8
        first = providers[0]
        assert all(p is first for p in providers), (
            "Multiple provider instances created under concurrency"
        )
        assert elapsed < 5, f"Concurrent load unexpectedly slow: {elapsed}s"
    finally:
        mm.LlamaCppProvider = orig  # type: ignore
