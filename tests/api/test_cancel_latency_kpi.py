import os
import json
import time
import pytest
from fastapi.testclient import TestClient
from mia4.api.app import app
from core.events import on, reset_listeners_for_tests


class _SlowStubProvider:
    def __init__(self):
    # Harmony stream: analysis first, then many small final chunks
        chunks = [
            "<|start|>assistant<|channel|>analysis<|message|>warmup<|end|>",
            "<|start|>assistant<|channel|>final<|message|>",
        ]
        chunks += ["chunk%02d " % i for i in range(40)]
        chunks += ["tail<|end|>"]
        self._output = chunks
        self._idx = 0

    def info(self):  # noqa: D401
        from types import SimpleNamespace
        return SimpleNamespace(
            role="primary",
            metadata={"passport_sampling_defaults": {"max_output_tokens": 64}},
        )

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        for part in self._output:
            time.sleep(0.03)
            yield part


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_cancel_latency_event_and_metric_under_kpi(monkeypatch, tmp_path):
    # Minimal config
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: abortModel\n"
            "    max_output_tokens: 64\n"
            "  reasoning_presets:\n"
            "    low: { reasoning_max_tokens: 16,\n"
            "           temperature: 0.7, top_p: 0.9 }\n"
            "postproc:\n"
            "  enabled: true\n"
            "  reasoning: { max_tokens: 32, drop_from_history: true }\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)

    # Patch get_model to stub
    from core.llm import factory as factory_mod
    from mia4.api.routes import generate as generate_route

    monkeypatch.setattr(
        factory_mod, "get_model", lambda *a, **k: _SlowStubProvider()
    )
    monkeypatch.setattr(
        generate_route, "get_model", lambda *a, **k: _SlowStubProvider()
    )
    client = TestClient(app)
    reset_listeners_for_tests()
    seen = []
    on(lambda n, p: seen.append((n, p)))
    with client.stream(
        "POST",
        "/generate",
        json={
            "session_id": "sess-kpi",
            "model": "abortModel",
            "prompt": "hi",
            "overrides": {"dev_per_token_delay_ms": 3},
        },
    ) as resp:
        assert resp.status_code == 200
        req_id = None
        start = None
        aborted = False
        from mia4.api import abort_registry
        for line in resp.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="ignore")
            if not line.startswith("data: "):
                continue
            try:
                obj = json.loads(line[len("data: "):])
            except Exception:
                continue
            if not req_id:
                req_id = obj.get("request_id")
                if req_id and not aborted:
                    abort_registry.mark_start(req_id)
                    start = time.time()
                    abort_registry.abort(req_id)
                    aborted = True
        assert req_id is not None
        assert start is not None
        elapsed_ms = int((time.time() - start) * 1000)
        assert elapsed_ms < 500
    names = [n for n, _ in seen]
    # Allow brief time for late-abort emission
    if "GenerationCancelled" not in names:
        t_wait = time.time()
        while (
            "GenerationCancelled" not in names
            and (time.time() - t_wait) < 1.5
        ):
            time.sleep(0.02)
            names = [n for n, _ in seen]
    assert "GenerationCancelled" in names
    # Allow brief time for cleanup-finalizer emission
    t0 = time.time()
    while "CancelLatencyMeasured" not in names and (time.time() - t0) < 1.5:
        time.sleep(0.02)
        names = [n for n, _ in seen]
    assert "CancelLatencyMeasured" in names
