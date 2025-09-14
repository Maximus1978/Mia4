import os
import json
from fastapi.testclient import TestClient
from core import metrics
from core.events import reset_listeners_for_tests
from mia4.api.app import app


class _ToolStubProviderOversize:
    def info(self):
        from types import SimpleNamespace
        return SimpleNamespace(
            role="primary",
            metadata={"passport_sampling_defaults": {"max_output_tokens": 16}},
        )

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        # Emit a too-large tool JSON (>8KB) then final
        big_args = {"k": "x" * 9000}
        payload = json.dumps({"tool": "oversize.test", "arguments": big_args})
        yield (
            "<|start|>assistant<|channel|>tool<|message|>" +
            payload +
            "<|end|>"
        )
        yield (
            "<|start|>assistant<|channel|>final<|message|>Done<|end|>"
        )


class _ToolStubProviderMalformed:
    def info(self):
        from types import SimpleNamespace
        return SimpleNamespace(
            role="primary",
            metadata={"passport_sampling_defaults": {"max_output_tokens": 16}},
        )

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        # Emit malformed JSON (missing closing brace)
        payload = '{"tool":"broken","arguments":{"a":1}'  # missing final }
        yield (
            "<|start|>assistant<|channel|>tool<|message|>" +
            payload +
            "<|end|>"
        )
        yield (
            "<|start|>assistant<|channel|>final<|message|>Done<|end|>"
        )


def _patch(monkeypatch, provider):
    from core.llm import factory as factory_mod
    from mia4.api.routes import generate as generate_route
    monkeypatch.setattr(factory_mod, "get_model", lambda *a, **k: provider)
    monkeypatch.setattr(generate_route, "get_model", lambda *a, **k: provider)


def _base_cfg(tmp_path):
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
            "postproc:\n"
            "  enabled: true\n"
            "  reasoning: { max_tokens: 4, drop_from_history: true }\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)
    return cfg_dir


def test_tool_call_oversize_payload(monkeypatch, tmp_path):  # noqa: D401
    _base_cfg(tmp_path)
    provider = _ToolStubProviderOversize()
    _patch(monkeypatch, provider)
    metrics.reset_for_tests()
    reset_listeners_for_tests()
    client = TestClient(app)
    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": "s_ov",
            "model": "toolModel",
            "prompt": "Hi",
        },
    ) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
        assert "toolModel" in body
    snap = metrics.snapshot()
    # Look for tool_calls_total with status=error
    counters = snap.get("counters", {})
    assert any(
        k.startswith("tool_calls_total") and "status=error" in k
        for k in counters.keys()
    ), counters.keys()


def test_tool_call_malformed_payload(monkeypatch, tmp_path):  # noqa: D401
    _base_cfg(tmp_path)
    provider = _ToolStubProviderMalformed()
    _patch(monkeypatch, provider)
    metrics.reset_for_tests()
    reset_listeners_for_tests()
    client = TestClient(app)
    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": "s_mal",
            "model": "toolModel",
            "prompt": "Hi",
        },
    ) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
        assert "toolModel" in body
    snap = metrics.snapshot()
    counters = snap.get("counters", {})
    assert any(
        k.startswith("tool_calls_total") and "status=error" in k
        for k in counters.keys()
    ), counters.keys()
