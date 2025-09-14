import pytest
from core.modules.module_manager import get_module_manager
from core.events import subscribe, reset_listeners_for_tests


class FakeCompleted:
    def __init__(self, stdout: str):
        self.stdout = stdout
        self.returncode = 0


@pytest.mark.skip("Downgrade logic removed in simplified provider")
def test_model_downgraded_low_vram(monkeypatch):
    reset_listeners_for_tests()
    received = []

    def handler(name, payload):  # noqa: D401
        if name in {"ModelDowngraded", "ModelLoaded"}:
            received.append((name, payload))

    unsub = subscribe(handler)
    try:
        # Monkeypatch subprocess.run in llama_cpp_provider scope
        import core.llm.llama_cpp_provider as prov

        def fake_run(cmd, capture_output, text, timeout):  # noqa: D401, ARG001
            return FakeCompleted("512")  # 512 MB free => triggers downgrade

        monkeypatch.setattr(
            prov,
            "subprocess",
            type("S", (), {"run": staticmethod(fake_run)}),
        )
        # Also monkeypatch actual Llama class to avoid real load
        
        class DummyLlama:
            def __init__(self, **kwargs):  # noqa: D401
                self.kwargs = kwargs

            def __call__(self, *a, **k):  # pragma: no cover
                return {"choices": []}

        monkeypatch.setattr(prov, "Llama", DummyLlama)
        mm = get_module_manager()
        # Force config fake flag off; patched DummyLlama avoids real load.
        mm.get_provider_by_role("primary")
        assert any(n == "ModelDowngraded" for n, _ in received)
    finally:
        unsub()
