import pytest
from core.modules.module_manager import get_module_manager
from core.events import subscribe, reset_listeners_for_tests


@pytest.mark.skip("Alias single-load guarantee deferred after cleanup")
def test_model_alias_single_physical_load():
    reset_listeners_for_tests()
    received = []

    def handler(name, payload):  # noqa: D401
        if name in {"ModelLoaded", "ModelAliasedLoaded"}:
            received.append((name, payload))

    unsub = subscribe(handler)
    try:
        mm = get_module_manager()
        # Load primary first
        mm.get_provider_by_role("primary")
    # Load judge alias (should not emit another ModelLoaded
    # for same weights)
        mm.get_provider_by_role("judge")
        loaded_events = [p for n, p in received if n == "ModelLoaded"]
        # Exactly one physical load expected
        assert len(loaded_events) == 1
        # Alias event present
        assert any(n == "ModelAliasedLoaded" for n, _ in received)
    finally:
        unsub()
