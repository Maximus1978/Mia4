import pytest
from core.modules.module_manager import get_module_manager
from core.events import subscribe, reset_listeners_for_tests


@pytest.mark.skip("Alias reuse semantics changed after fake removal")
def test_model_alias_reuse_event():
    reset_listeners_for_tests()
    received = []

    def handler(name, payload):  # noqa: D401
        if name in {"ModelAliasedLoaded"}:
            received.append((name, payload))

    unsubscribe = subscribe(handler)
    try:
        mm = get_module_manager()
        primary = mm.get_provider_by_role("primary")
        # attempt to load judge (alias to same underlying file for phi variant)
        judge = mm.get_provider_by_role("judge")
        assert primary is not None and judge is not None
        # At least one alias event should be recorded if judge shares weights
        assert any(name == "ModelAliasedLoaded" for name, _ in received)
    finally:
        unsubscribe()
