import os
from pathlib import Path
from fastapi.testclient import TestClient

from mia4.api.app import app
from core import metrics
from core.events import reset_listeners_for_tests


class _StubInfo:
    def __init__(self, role: str = "primary"):
        self.role = role
        self.metadata = {"passport_sampling_defaults": {}}


class _Provider:
    def __init__(self, output: str):
        self._output = output
    
    def info(self):
        return _StubInfo()
    
    def stream(self, prompt: str, **kwargs):

        # emit full output in one chunk
        yield self._output


def _make_config(tmp: Path):
    cfg_dir = tmp / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: m1\n"
            "    temperature: 0.7\n"
            "    top_p: 0.9\n"
            "    max_output_tokens: 128\n"
            "    n_gpu_layers: 0\n"
            "  lightweight:\n"
            "    id: m1-lite\n"
            "    temperature: 0.4\n"
            "  reasoning_presets:\n"
            "    medium:\n"
            "      temperature: 0.7\n"
            "      top_p: 0.9\n"
            "      reasoning_max_tokens: 32\n"
            "  postproc:\n"
            "    enabled: true\n"
            "    reasoning:\n"
            "      max_tokens: 64\n"
            "      drop_from_history: true\n"
            "      ratio_alert_threshold: 0.5\n"
            "    ngram:\n"
            "      n: 3\n"
            "      window: 64\n"
            "    collapse:\n"
            "      whitespace: true\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)


def test_commentary_stream(tmp_path, monkeypatch):
    # analysis -> commentary -> final
    out = (
        "<|start|>assistant<|channel|>analysis<|message|>reason step<|end|>"
        "<|start|>assistant<|channel|>commentary<|message|>Plan: step1<|end|>"
        "<|start|>assistant<|channel|>final<|message|>ok result<|return|>"
    )
    provider = _Provider(out)

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

    commentary_seen = False
    analysis_seen = False
    final_seen = False

    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": "s1",
            "model": "m1",
            "prompt": "Q",
            "overrides": {"reasoning_preset": "medium"},
        },
    ) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("event: commentary"):
                commentary_seen = True
            if line.startswith("event: analysis"):
                analysis_seen = True
            if line.startswith("event: final"):
                final_seen = True
            if line.startswith("event: end"):
                break

    assert commentary_seen, "expected commentary event"
    assert analysis_seen, "expected analysis event"
    assert final_seen, "expected final event"
