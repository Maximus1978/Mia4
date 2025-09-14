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


class _ProviderBase:
    def __init__(self, output: str):
        self._output = output

    def info(self):  # noqa: D401
        return _StubInfo()

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        # Emit in two chunks to exercise peek logic
        mid = len(self._output) // 2
        yield self._output[:mid]
        yield self._output[mid:]


def _make_config(tmp: Path):  # noqa: D401
    cfg_dir = tmp / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: mLow\n"
            "    temperature: 0.7\n"
            "    top_p: 0.9\n"
            "    max_output_tokens: 128\n"
            "    n_gpu_layers: 0\n"
            "  lightweight:\n"
            "    id: mLow\n"
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


def test_reasoning_ratio_alert_below_and_above(
    tmp_path, monkeypatch
):  # noqa: D401
    # High ratio: many reasoning tokens vs few final tokens
    high_output = (
        "<|start|>assistant<|channel|>analysis<|message|>"
        + ("thought " * 20)
        + "<|end|><|start|>assistant<|channel|>final<|message|>short final."
        + "<|end|>"
    )
    # Low ratio: 1 reasoning token then many final tokens
    # Low ratio case: one reasoning token then many distinct final tokens.
    # Use distinct tokens to avoid n-gram suppression trimming the stream.
    distinct_final = " ".join([f"tok{i}" for i in range(25)]) + " "
    low_output = (
        "<|start|>assistant<|channel|>analysis<|message|>intro<|end|>"
        + "<|start|>assistant<|channel|>final<|message|>"
        + distinct_final
        + "<|end|>"
    )
    providers = {
        "mHigh": _ProviderBase(high_output),
        "mLow": _ProviderBase(low_output),
    }

    def _fake_get_model(model_id: str, repo_root: str = "."):
        return providers[model_id]

    from core.llm import factory as factory_mod
    from mia4.api.routes import generate as generate_route

    # Patch factory and already-imported symbol inside route.
    monkeypatch.setattr(factory_mod, "get_model", _fake_get_model)
    monkeypatch.setattr(generate_route, "get_model", _fake_get_model)

    _make_config(tmp_path)
    metrics.reset_for_tests()
    reset_listeners_for_tests()
    client = TestClient(app)

    # Below threshold case
    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": "s-low",
            "model": "mLow",
            "prompt": "Q",
            "overrides": {"reasoning_preset": "medium"},
        },
    ) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if line and line.startswith("event: end"):
                break

    # Above threshold case
    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": "s-high",
            "model": "mHigh",
            "prompt": "Q",
            "overrides": {"reasoning_preset": "medium"},
        },
    ) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if line and line.startswith("event: end"):
                break

    snap = metrics.snapshot()
    counters = snap.get("counters", {})
    above = [
        k
        for k in counters
        if k.startswith("reasoning_ratio_alert_total{")
        and "bucket=above" in k
    ]
    below = [
        k
        for k in counters
        if k.startswith("reasoning_ratio_alert_total{")
        and "bucket=below" in k
    ]
    assert above, f"expected above bucket increment, counters={counters}"
    assert below, f"expected below bucket increment, counters={counters}"
