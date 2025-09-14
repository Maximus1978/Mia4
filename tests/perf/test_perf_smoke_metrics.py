import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mia4.api.app import app
from core.events import reset_listeners_for_tests, on


class _PerfStubProvider:
    class _Info:
        id = "perfStub"
        role = "primary"
        metadata = {
            "stub": True,
            "passport_sampling_defaults": {"max_output_tokens": 64},
        }

    def info(self):
        return self._Info()

    def stream(self, prompt: str, **kwargs):  # noqa: D401
        # Emit a few fast tokens to exercise metrics
        t0 = time.time()
        # small artificial delay to have a measurable first token latency
        time.sleep(0.01)
        yield {"type": "delta", "text": "Hello"}
        yield {"type": "delta", "text": ", "}
        yield {"type": "delta", "text": "world"}
        yield {
            "type": "final",
            "stats": {"reasoning_ratio": 0.0},
            "final_detect_time": t0,
        }


@pytest.mark.performance
def test_perf_smoke_metrics(tmp_path, monkeypatch):
    # Isolated config root
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "modules:\n"
            "  enabled: [llm]\n"
            "llm:\n"
            "  primary:\n"
            "    id: perfStub\n"
            "    max_output_tokens: 32\n"
            "postproc:\n"
            "  enabled: true\n"
        ),
        encoding="utf-8",
    )
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)

    # Patch provider
    from core.llm import factory as factory_mod
    from mia4.api.routes import generate as generate_route

    monkeypatch.setattr(
        factory_mod, "get_model", lambda *a, **k: _PerfStubProvider()
    )
    monkeypatch.setattr(
        generate_route, "get_model", lambda *a, **k: _PerfStubProvider()
    )

    client = TestClient(app)
    reset_listeners_for_tests()
    seen = []
    on(lambda n, p: seen.append((n, p)))

    # Run three times to mimic smoke repetitions
    for i in range(3):
        with client.stream(
            "POST",
            "/generate",
            json={
                "session_id": f"perf-smoke-{i}",
                "model": "perfStub",
                "prompt": "ping",
                "overrides": {},
            },
        ) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if not line:
                    continue
                # drain
                if isinstance(line, bytes):
                    _ = line.decode("utf-8", errors="ignore")

    # Sanity: events must contain GenerationCompleted at least once
    names = [n for n, _ in seen]
    assert names.count("GenerationCompleted") >= 1

    # Produce a tiny snapshot file (best-effort)
    out = {
        "runs": 3,
        "model": "perfStub",
        "ts": int(time.time()),
        "notes": "perf smoke stub run",
    }
    reports = Path("reports")
    reports.mkdir(exist_ok=True)
    (reports / "perf_smoke_stub.json").write_text(
        json.dumps(out), encoding="utf-8"
    )
