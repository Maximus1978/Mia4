from core.events import GenerationStarted, reset_listeners_for_tests, on
from core.config import get_config
from core.llm.factory import get_model
import hashlib


def test_generation_started_includes_system_prompt(monkeypatch):
    reset_listeners_for_tests()
    captured = {}

    def handler(name, payload):  # noqa: D401
        if name == "GenerationStarted":
            captured.update(payload)

    on(handler)
    cfg = get_config().llm
    # Ensure system_prompt text present
    assert cfg.system_prompt.get("text"), "system_prompt text empty in config"
    provider = get_model(cfg.primary.id, repo_root=".")
    base_sp = cfg.system_prompt["text"].strip()
    expected_hash = hashlib.sha256(base_sp.encode("utf-8")).hexdigest()[:16]
    # Emit manually (unit scope)
    evt = GenerationStarted(
        request_id="r1",
        model_id=cfg.primary.id,
        role=provider.info().role,
        prompt_tokens=3,
        system_prompt_version=cfg.system_prompt["version"],
        system_prompt_hash=expected_hash,
        persona_len=0,
    )
    from core.events import emit  # local import to avoid cycles
    emit(evt)
    assert (
        captured.get("system_prompt_version")
        == cfg.system_prompt["version"]
    ), captured
    assert captured.get("system_prompt_hash") == expected_hash, captured
    assert captured.get("persona_len") == 0, captured
