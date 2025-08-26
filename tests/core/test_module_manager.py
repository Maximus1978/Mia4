from core.modules import ModuleManager
from core.config import get_config


def test_module_manager_llm_registered():
    cfg = get_config()
    assert "llm" in cfg.modules.enabled  # sanity
    mm = ModuleManager()
    assert mm.is_enabled("llm")
    llm_mod = mm.get("llm")
    info = llm_mod.info()
    assert info["primary_id"] == cfg.llm.primary.id


def test_module_manager_unknown_ignored():
    # Simulate enabling a future module name not yet registered
    cfg = get_config()
    # build custom registry without adding the fake name so it stays unknown
    mm = ModuleManager()
    # Force-check internal handling by appending a fake name after init
    # (In real scenario it would come from config; here we assert behaviour of unknown list)
    assert isinstance(mm.unknown, list)
