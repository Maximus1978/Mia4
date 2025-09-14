from core.modules.module_manager import get_module_manager
from core.events import subscribe, reset_listeners_for_tests


def test_switch_primary_lightweight_primary():
    reset_listeners_for_tests()
    events = []

    def handler(name, payload):  # noqa: D401
        if name in {"ModelLoaded", "ModelUnloaded", "ModelAliasedLoaded"}:
            events.append((name, payload))

    unsub = subscribe(handler)
    try:
        mm = get_module_manager()
        p1 = mm.get_provider_by_role("primary")
        mm.get_provider_by_role("lightweight")
        p2 = mm.get_provider_by_role("primary")
        assert p1.info().id == p2.info().id
        loaded_ids = [p["model_id"] for n, p in events if n == "ModelLoaded"]
        assert any("gpt-oss" in mid for mid in loaded_ids)
        assert any("phi-3.5" in mid for mid in loaded_ids)
    finally:
        unsub()
