import os


class _Prov:
    def info(self):  # noqa: D401
        from types import SimpleNamespace
        # Small context to force trimming
        return SimpleNamespace(
            id="m",
            role="primary",
            context_length=1024,
            metadata={},
        )

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
            "    low: { reasoning_max_tokens: 16, temperature: 0.7, "
            "top_p: 0.9 }\n"
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


def test_current_prompt_always_present(tmp_path):  # noqa: D401
    from core.llm.pipeline.primary import PrimaryPipeline

    _cfg(tmp_path)
    prov = _Prov()
    pipe = PrimaryPipeline()

    # History ends with assistant; current user prompt is new
    history = []
    for i in range(10):
        history.append(("user", f"u{i}=" + ("x" * 120)))
        history.append(("assistant", f"a{i}=" + ("y" * 120)))
    assert history[-1][0] == "assistant"

    ctx = pipe.prepare(
        request_id="r2",
        model_id="m1",
        provider=prov,
        prompt="fresh user question?",
        session_messages=history,
        reasoning_mode="low",
        user_sampling={"max_tokens": 64},
        passport_defaults={"max_output_tokens": 64},
        sampling_origin="mixed",
    )

    # Must include the current user prompt even if history ended with assistant
    assert "fresh user question?" in ctx.prompt


def test_output_reserve_affects_budget(tmp_path):  # noqa: D401
    from core.llm.pipeline.primary import PrimaryPipeline

    _cfg(tmp_path)
    prov = _Prov()  # context_length=1024 per _Prov.info()
    pipe = PrimaryPipeline()

    # Build sizeable history so trimming is necessary
    history = []
    for i in range(30):
        history.append(("user", f"u{i}=" + ("x" * 150)))
        history.append(("assistant", f"a{i}=" + ("y" * 150)))

    # Smaller reserve (64) should keep more history than larger reserve (256)
    ctx_small_reserve = pipe.prepare(
        request_id="r3",
        model_id="m1",
        provider=prov,
        prompt="reserve-64",
        session_messages=history,
        reasoning_mode="low",
        user_sampling={"max_tokens": 64},
        passport_defaults={"max_output_tokens": 64},
        sampling_origin="mixed",
    )
    ctx_large_reserve = pipe.prepare(
        request_id="r4",
        model_id="m1",
        provider=prov,
        prompt="reserve-256",
        session_messages=history,
        reasoning_mode="low",
        user_sampling={"max_tokens": 256},
        passport_defaults={"max_output_tokens": 256},
        sampling_origin="mixed",
    )

    # Earlier markers should drop sooner for larger reserve. Compare earliest
    # surviving marker index in both prompts.
    import re as _re

    def earliest_idx(s: str) -> int | None:
        nums = []
        for m in _re.finditer(r"[ua](\d+)=", s):
            try:
                nums.append(int(m.group(1)))
            except Exception:
                continue
        return min(nums) if nums else None

    small_min = earliest_idx(ctx_small_reserve.prompt)
    large_min = earliest_idx(ctx_large_reserve.prompt)
    # Ensure the scenario is meaningful: at least one marker present in small
    assert small_min is not None
    # With larger reserve, earliest surviving index should be >= (not earlier)
    if large_min is not None:
        assert large_min >= small_min
