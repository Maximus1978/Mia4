from core.events import on, reset_listeners_for_tests
from core import metrics
from fastapi.testclient import TestClient
from mia4.api.app import app
import os


def test_sampling_generation_started_matches_completed(tmp_path):
    cfg_dir = tmp_path / 'configs'
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath('base.yaml').write_text(
        (
            'modules:\n'
            '  enabled: [llm]\n'
            'llm:\n'
            '  primary:\n'
            '    id: syncModel\n'
            '    max_output_tokens: 24\n'
            'postproc:\n'
            '  enabled: true\n'
            '  reasoning: { max_tokens: 4, drop_from_history: true }\n'
        ), encoding='utf-8')
    os.environ['MIA_CONFIG_DIR'] = str(cfg_dir)
    metrics.reset_for_tests()
    reset_listeners_for_tests()
    started = []
    completed = []

    def _h(name, payload):  # noqa: D401
        if name == 'GenerationStarted':
            started.append(payload)
        if name == 'GenerationCompleted':
            completed.append(payload)

    on(_h)
    client = TestClient(app)
    r = client.post('/generate', json={
        'session_id': 's1',
        'model': 'syncModel',
        'prompt': 'Hello',
        'overrides': {'max_output_tokens': 40}
    })
    assert r.status_code == 200
    assert started and completed, 'events missing'
    gs = started[0]['sampling']
    # Use last GenerationCompleted (pipeline finalization) in case
    # provider emitted an earlier stub event without summary.
    gc_event = completed[-1]
    assert gc_event.get('result_summary'), (
        'pipeline finalization missing result_summary'
    )
    gc = gc_event['result_summary']['sampling']
    assert gs['effective_max_tokens'] == gc['effective_max_tokens']
    assert bool(gs['cap_applied']) == bool(gc['cap_applied'])
    assert gs.get('cap_source') == gc.get('cap_source')
