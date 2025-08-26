from core.modules.module_manager import get_module_manager


def test_capability_routing_judge_specific():
    mm = get_module_manager()
    llm = mm.get("llm")
    provider = llm.get_provider_by_capabilities(["judge"], skip_checksum=True)
    assert "judge" in provider.info().capabilities


def test_capability_routing_fallback_primary():
    mm = get_module_manager()
    llm = mm.get("llm")
    provider = llm.get_provider_by_capabilities(["nonexistent_cap"])  # fallback
    assert provider.info().id == llm.get_provider_by_role("primary").info().id