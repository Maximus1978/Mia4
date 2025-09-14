import threading
import time

from core.modules.module_manager import LLMModule
from core.config import get_config


def test_llmmodule_concurrent_load_single_instance():
    cfg = get_config().llm
    primary_id = cfg.primary.id

    # Monkeypatch heavy provider with lightweight fake (no real model load)
    from core.modules import module_manager as mm

    class FakeProvider:  # minimal stub
        def __init__(self, **kw):  # noqa: D401, ANN001
            self._id = kw.get("model_id")
            self._role = kw.get("role")
            self._loaded = False

        def load(self):  # noqa: D401
            self._loaded = True

        def generate(self, prompt: str, **_: object):  # noqa: D401
            class R:
                text = "stub"
                usage = type(
                    "U",
                    (),
                    {"prompt_tokens": 1, "completion_tokens": 1},
                )()
                timings = type(
                    "T", (), {"total_ms": 1, "decode_tps": 1.0}
                )()
                model_id = self._id
                role = self._role
                request_id = "r"
                status = "ok"
            return R()

        def stream(self, prompt: str, **_: object):  # noqa: D401
            yield "stub"

        def info(self):  # noqa: D401
            from core.llm import ModelInfo
            return ModelInfo(
                id=self._id,
                role=self._role,
                capabilities=("chat",),
                context_length=128,
            )

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
