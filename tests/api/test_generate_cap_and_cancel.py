import os
import time
from fastapi.testclient import TestClient

from mia4.api.app import app
from core import metrics
from core.events import reset_listeners_for_tests


class _CapStubProvider:
    def __init__(self):
        self._output = ["token " for _ in range(50)]

    def info(self):
        from types import SimpleNamespace
        return SimpleNamespace(
            role="primary",
            metadata={
                "passport_sampling_defaults": {"max_output_tokens": 8}
            },
        )

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        for part in self._output:
            time.sleep(0.005)
            yield part


def _patch(monkeypatch):
    from core.llm import factory as factory_mod
    from mia4.api.routes import generate as generate_route
    monkeypatch.setattr(
        factory_mod, "get_model", lambda *a, **k: _CapStubProvider()
    )
    monkeypatch.setattr(
        generate_route, "get_model", lambda *a, **k: _CapStubProvider()
    )


def test_cap_applied_and_metric(monkeypatch, tmp_path):  # noqa: D401
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: capModel\n"
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
            "model": "capModel",
            "prompt": "Hello",
            "overrides": {"reasoning_preset": "low", "max_output_tokens": 32},
        },
    ) as r:
        assert r.status_code == 200
        body = "".join([chunk for chunk in r.iter_text()])
        assert "\"cap_applied\": true" in body or "cap_applied\": true" in body
    snap_full = metrics.snapshot()
    legacy = snap_full.get("counters_legacy", {})
    assert any(k[0] == "model_cap_hits_total" for k in legacy.keys())


def test_cancel_user_abort(monkeypatch, tmp_path):  # noqa: D401
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: cancelModel\n"
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

    # We can't get request_id until events; simulate by issuing abort on
    # unknown id (no-op) then rely on metrics.
    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": "s1",
            "model": "cancelModel",
            "prompt": "Hi",
            "overrides": {
                "reasoning_preset": "low",
                "dev_per_token_delay_ms": 20,
            },
        },
    ) as r:
        assert r.status_code == 200
        # Abort unknown
        client.post("/generate/abort", json={"request_id": "unknown-id"})
    # Stream closed gracefully; metrics show cancel path.
    snap_full = metrics.snapshot()
    legacy = snap_full.get("counters_legacy", {})
    # cancellation metric may appear as generation_cancelled_total
    cancelled_metric = any(
        k[0] == "generation_cancelled_total" for k in legacy.keys()
    )
    aborted_metric = any(
        k[0] == "generation_aborted_total" for k in legacy.keys()
    )
    assert cancelled_metric or aborted_metric
