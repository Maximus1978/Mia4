from core.events import on, reset_listeners_for_tests
from core import metrics
from fastapi.testclient import TestClient
from mia4.api.app import app
import os


def test_model_routed_and_sampling(monkeypatch, tmp_path):
    cfg_dir = tmp_path / 'configs'
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath('base.yaml').write_text(
        (
            'modules:\n'
            '  enabled: [llm]\n'
            'llm:\n'
            '  primary:\n'
            '    id: routedModel\n'
            '    max_output_tokens: 32\n'
            'postproc:\n'
            '  enabled: true\n'
            '  reasoning: { max_tokens: 4, drop_from_history: true }\n'
        ), encoding='utf-8')
    os.environ['MIA_CONFIG_DIR'] = str(cfg_dir)
    metrics.reset_for_tests()
    reset_listeners_for_tests()
    events = []

    def _h(name, payload):
        if name in {'ModelRouted', 'GenerationStarted'}:
            events.append((name, payload))

    on(_h)
    client = TestClient(app)
    r = client.post('/generate', json={
        'session_id': 's1',
        'model': 'routedModel',
        'prompt': 'Hi',
        'overrides': {'max_output_tokens': 64}
    })
    assert r.status_code == 200
    names = [n for n, _ in events]
    assert 'ModelRouted' in names, f'Events: {names}'
    assert 'GenerationStarted' in names, f'Events: {names}'
    # Sampling in GenerationStarted should reflect cap to 32 (passport absent)
    gs = next(p for n, p in events if n == 'GenerationStarted')
    sampling = gs.get('sampling') or {}
    assert (
        sampling.get('effective_max_tokens')
        <= sampling.get('requested_max_tokens')
    )
    # cap_applied True because override (64) > cfg limit (32)
    assert sampling.get('cap_applied') is True
