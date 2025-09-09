import os
import pytest
from fastapi.testclient import TestClient
from core import metrics
from core.events import reset_listeners_for_tests
from mia4.api.app import app


class _ToolStubProvider:
    def info(self):
        from types import SimpleNamespace
        return SimpleNamespace(
            role="primary",
            metadata={"passport_sampling_defaults": {"max_output_tokens": 16}},
        )

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        # Emit a tool channel followed by final
        yield (
            "<|start|>assistant<|channel|>tool<|message|>" +
            '{"tool":"search.web","arguments":{"q":"cats"}}' +
            "<|end|>"
        )
        yield (
            "<|start|>assistant<|channel|>final<|message|>Done<|end|>"
        )


def _patch(monkeypatch):
    from core.llm import factory as factory_mod
    from mia4.api.routes import generate as generate_route
    monkeypatch.setattr(
        factory_mod, "get_model", lambda *a, **k: _ToolStubProvider()
    )
    monkeypatch.setattr(
        generate_route, "get_model", lambda *a, **k: _ToolStubProvider()
    )


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_tool_call_events_and_metrics(monkeypatch, tmp_path):  # noqa: D401
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: toolModel\n"
            "    max_output_tokens: 64\n"
            "  reasoning_presets:\n"
            "    low: { reasoning_max_tokens: 4, temp: 0.7, top_p: 0.9 }\n"
            "postproc:\n"
            "  enabled: true\n"
            "  reasoning: { max_tokens: 8, drop_from_history: true }\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)
    _patch(monkeypatch)
    metrics.reset_for_tests()
    reset_listeners_for_tests()
    client = TestClient(app)

    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": "s1",
            "model": "toolModel",
            "prompt": "Hello",
            "overrides": {"reasoning_preset": "low"},
        },
    ) as r:
        assert r.status_code == 200
        body = "".join([chunk for chunk in r.iter_text()])
        assert "toolModel" in body  # basic sanity
    snap = metrics.snapshot()
    counters = snap.get("counters", {})
    # Ensure tool_calls_total counter exists (status ok)
    assert any(k.startswith("tool_calls_total") for k in counters.keys())
    hist = snap.get("histograms", {})
    assert any(k.startswith("tool_call_latency_ms") for k in hist.keys())
