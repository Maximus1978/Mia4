from core import metrics
from core.events import on, reset_listeners_for_tests
from fastapi.testclient import TestClient
from mia4.api.app import app
import os
import time
import pytest


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_cancel_latency_measured(tmp_path):  # noqa: D401
    cfg_dir = tmp_path / 'configs'
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath('base.yaml').write_text(
        (
            'modules:\n'
            '  enabled: [llm]\n'
            'llm:\n'
            '  primary:\n'
            '    id: cancelLatency\n'
            '    max_output_tokens: 32\n'
            'postproc:\n'
            '  enabled: true\n'
            '  reasoning: { max_tokens: 4, drop_from_history: true }\n'
        ),
        encoding='utf-8'
    )
    os.environ['MIA_CONFIG_DIR'] = str(cfg_dir)
    metrics.reset_for_tests()
    reset_listeners_for_tests()
    events = []
    on(lambda n, p: events.append((n, p)))

    class _Prov:
        def info(self):
            from types import SimpleNamespace
            return SimpleNamespace(role='primary', metadata={})

        def stream(self, prompt: str, **kw):
            for _ in range(20):
                time.sleep(0.01)
                yield 'tok'
    from core.llm import factory as factory_mod
    from mia4.api.routes import generate as generate_route
    factory_mod.get_model = lambda *a, **k: _Prov()  # type: ignore
    generate_route.get_model = lambda *a, **k: _Prov()  # type: ignore

    client = TestClient(app)
    with client.stream('POST', '/generate', json={
        'session_id': 's1', 'model': 'cancelLatency', 'prompt': 'Hi'
    }) as r:
        assert r.status_code == 200
        # Issue abort quickly
        rid = events[0][1]['request_id'] if events else 'unknown'
        client.post('/generate/abort', json={'request_id': rid})
        # Consume until end to ensure finalize path executes
        for line in r.iter_lines():
            if line.startswith('event: end'):
                break
    snap = metrics.snapshot()
    hist = snap['histograms']
    # Expect at least one latency measurement
    assert any(k.startswith('cancel_latency_ms') for k in hist), hist
