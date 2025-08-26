from core.modules.module_manager import get_module_manager


def test_llm_module_routing_primary_info():
    mm = get_module_manager()
    llm = mm.get("llm")
    info = llm.info()
    assert info["primary_id"] is not None


def test_llm_module_get_provider_by_role_fallback():
    mm = get_module_manager()
    llm = mm.get("llm")
    primary = llm.get_provider_by_role("primary")
    fake = llm.get_provider_by_role("nonexistent_role")
    assert primary.info().id == fake.info().id


def test_llm_module_capability_routing_fallback():
    mm = get_module_manager()
    llm = mm.get("llm")
    # capability unlikely to exist → fallback to primary
    p = llm.get_provider_by_capabilities(["nonexistent_cap"])
    assert p.info().id == llm.get_provider_by_role("primary").info().id