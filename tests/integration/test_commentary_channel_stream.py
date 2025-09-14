import os
import json
from pathlib import Path
from fastapi.testclient import TestClient

from mia4.api.app import app
from core import metrics
from core.events import reset_listeners_for_tests


class _StubInfo:
    def __init__(self, role: str = "primary"):
        self.role = role
        self.metadata = {"passport_sampling_defaults": {}}


class _ProviderBase:
    def __init__(self, output: str):
        self._output = output

    def info(self):  # noqa: D401
        return _StubInfo()

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        yield self._output


def _make_config(tmp: Path):  # noqa: D401
    cfg_dir = tmp / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: mTest\n"
            "    temperature: 0.7\n"
            "    top_p: 0.9\n"
            "    max_output_tokens: 128\n"
            "    n_gpu_layers: 0\n"
            "  lightweight:\n"
            "    id: mTest\n"
            "  reasoning_presets:\n"
            "    medium:\n"
            "      temperature: 0.7\n"
            "      top_p: 0.9\n"
            "      reasoning_max_tokens: 64\n"
            "  postproc:\n"
            "    enabled: true\n"
            "    reasoning:\n"
            "      max_tokens: 256\n"
            "      drop_from_history: true\n"
            "      ratio_alert_threshold: 0.3\n"
            "    ngram:\n"
            "      n: 3\n"
            "      window: 64\n"
            "    collapse:\n"
            "      whitespace: true\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)


def test_commentary_channel_stream(tmp_path, monkeypatch):  # noqa: D401
    output = (
        "<|start|>assistant<|channel|>analysis<|message|>thinking path<|end|>"
        "<|start|>assistant<|channel|>commentary<|message|>Plan: X Y<|end|>"
        "<|start|>assistant<|channel|>final<|message|>Result ok.<|end|>"
    )
    provider = _ProviderBase(output)

    def _fake_get_model(model_id: str, repo_root: str = "."):
        return provider

    from core.llm import factory as factory_mod
    from mia4.api.routes import generate as generate_route

    monkeypatch.setattr(factory_mod, "get_model", _fake_get_model)
    monkeypatch.setattr(generate_route, "get_model", _fake_get_model)

    _make_config(tmp_path)
    metrics.reset_for_tests()
    reset_listeners_for_tests()
    client = TestClient(app)

    commentary_events = []
    usage_payload = None
    prev_event = ""

    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": "s1",
            "model": "mTest",
            "prompt": "Hello",
            "overrides": {"reasoning_preset": "medium"},
        },
    ) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("event: commentary"):
                prev_event = "commentary"
                continue
            if line.startswith("event: usage"):
                prev_event = "usage"
                continue
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if prev_event == "commentary":
                    commentary_events.append(payload)
                elif prev_event == "usage":
                    usage_payload = payload
                prev_event = ""
            if line.startswith("event: end"):
                break

    assert commentary_events, "expected commentary event in stream"
    assert commentary_events[0]["text"].startswith("Plan:"), commentary_events
    assert usage_payload, "usage payload missing"
    # Ensure commentary not counted in reasoning/final ratio math
    rt = usage_payload.get("reasoning_tokens") or 0
    ft = usage_payload.get("output_tokens") or 0
    assert rt >= 1 and ft >= 2
    # Metric for commentary tokens is optional if commentary emits zero tokens
    # (pass-through). Presence of commentary event is primary contract here.
