from core.events import on, reset_listeners_for_tests, GenerationStarted
from core.llm.factory import get_model, clear_provider_cache
from core.config import get_config


def test_passport_sampling_defaults_merged():
    cfg = get_config().llm
    primary_id = cfg.primary.id
    # Clear any previously loaded provider so passport attaches during load
    clear_provider_cache()
    provider = get_model(primary_id, repo_root=".")
    # Ensure passport info attached
    info = provider.info()
    meta = info.metadata or {}
    # passport file was added in models/<id>/passport.yaml
    assert meta.get("passport_version") == 1, meta
    assert meta.get("passport_hash"), meta
    defaults = meta.get("passport_sampling_defaults") or {}
    # temperature from passport should be 1.0 (overriding config 0.7)
    assert defaults.get("temperature") == 1.0, defaults

    captured = {}
    reset_listeners_for_tests()

    def handler(name, payload):  # noqa: D401
        if name == "GenerationStarted":
            captured.update(payload)

    on(handler)
    # Emit a synthetic GenerationStarted with merged info similar to route
    evt = GenerationStarted(
        request_id="rX",
        model_id=primary_id,
        role=provider.info().role,
        prompt_tokens=5,
        system_prompt_version=None,
        system_prompt_hash=None,
        persona_len=0,
        sampling_origin="passport",
        merged_sampling=defaults,
    )
    from core.events import emit

    emit(evt)
    assert captured.get("sampling_origin") == "passport", captured
    assert captured.get("merged_sampling") == defaults, captured
