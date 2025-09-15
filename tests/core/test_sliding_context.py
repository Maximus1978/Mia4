import os
from mia4.api.session_store import ChatMessage


class _Prov:
    def info(self):  # noqa: D401
        from types import SimpleNamespace
        # Small context to force trimming
        return SimpleNamespace(id="m", role="primary", context_length=1024, metadata={})

    def stream(self, prompt: str, **kw):  # pragma: no cover - not used here
        yield "ok"


def _cfg(tmp_path):
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: test\n"
            "    max_output_tokens: 64\n"
            "  reasoning_presets:\n"
            "    low: { reasoning_max_tokens: 16, temperature: 0.7, top_p: 0.9 }\n"
            "  system_prompt:\n"
            "    text: 'System base'\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)


def test_sliding_window_drops_oldest(tmp_path):  # noqa: D401
    from core.llm.pipeline.primary import PrimaryPipeline

    _cfg(tmp_path)
    prov = _Prov()
    pipe = PrimaryPipeline()

    # Build history longer than budget
    history = []
    for i in range(20):
        history.append(("user", f"u{i}=" + ("x" * 80)))
        history.append(("assistant", f"a{i}=" + ("y" * 80)))

    ctx = pipe.prepare(
        request_id="r1",
        model_id="m1",
        provider=prov,
        prompt="current user question?",
        session_messages=history,
        reasoning_mode="low",
        user_sampling={"max_tokens": 64},
        passport_defaults={"max_output_tokens": 64},
        sampling_origin="mixed",
    )

    # Expect earliest markers to be trimmed from the prompt string
    assert "u0=" not in ctx.prompt
    assert "a0=" not in ctx.prompt
    # Latest items and current prompt should be present
    assert "current user question?" in ctx.prompt
    assert "u19=" in ctx.prompt or "a19=" in ctx.prompt
