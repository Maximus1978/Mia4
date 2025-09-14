from core.events import on, reset_listeners_for_tests
from core import metrics
from fastapi.testclient import TestClient
from mia4.api.app import app
import os


def test_model_passport_mismatch_event(tmp_path):  # noqa: D401
    cfg_dir = tmp_path / 'configs'
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath('base.yaml').write_text(
        (
            'modules:\n'
            '  enabled: [llm]\n'
            'llm:\n'
            '  primary:\n'
            '    id: mismatchModel\n'
            '    max_output_tokens: 32\n'
            'postproc:\n'
            '  enabled: true\n'
            '  reasoning: { max_tokens: 4, drop_from_history: true }\n'
        ),
        encoding='utf-8'
    )
    # Stub provider with passport declaring different limit
    class _Prov:
        def info(self):  # noqa: D401
            from types import SimpleNamespace
            return SimpleNamespace(
                role='primary',
                metadata={
                    'passport_sampling_defaults': {
                        'max_output_tokens': 16
                    }
                },
            )

        def stream(self, prompt: str, **kw):  # noqa: D401
            yield 'Hi'
    from core.llm import factory as factory_mod
    from mia4.api.routes import generate as generate_route
    os.environ['MIA_CONFIG_DIR'] = str(cfg_dir)
    metrics.reset_for_tests()
    reset_listeners_for_tests()
    events = []
    on(lambda n, p: events.append((n, p)))
    factory_mod.get_model = lambda *a, **k: _Prov()  # type: ignore
    generate_route.get_model = lambda *a, **k: _Prov()  # type: ignore
    client = TestClient(app)
    r = client.post('/generate', json={
        'session_id': 's1',
        'model': 'mismatchModel',
        'prompt': 'Check',
    })
    assert r.status_code == 200, r.text
    # Ensure mismatch event present
    names = [n for n, _ in events]
    assert 'ModelPassportMismatch' in names, names
    snap = metrics.snapshot()
    counters = snap['counters']
    assert any(
        k.startswith('model_passport_mismatch_total{field=max_output_tokens}')
        for k in counters
    ), counters
