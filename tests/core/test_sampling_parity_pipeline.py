from core.events import on, reset_listeners_for_tests
from core import metrics
from fastapi.testclient import TestClient
from mia4.api.app import app
import os


def test_sampling_parity_started_completed(tmp_path):  # noqa: D401
    """Ensure GenerationStarted.sampling mirrors
    GenerationCompleted.result_summary.sampling.

    ADR-0028 invariant: sampling requested/effective & cap flags
    identical across start and completion events (no re-derivation).
    """
    cfg_dir = tmp_path / 'configs'
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath('base.yaml').write_text(
        (
            'modules:\n'
            '  enabled: [llm]\n'
            'llm:\n'
            '  primary:\n'
            '    id: parityModel\n'
            '    max_output_tokens: 16\n'
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

    def _h(name, payload):
        if name in {'GenerationStarted', 'GenerationCompleted'}:
            events.append((name, payload))

    on(_h)
    client = TestClient(app)
    r = client.post('/generate', json={
        'session_id': 's1',
        'model': 'parityModel',
        'prompt': 'Hello parity',
        'overrides': {'max_output_tokens': 32}
    })
    assert r.status_code == 200, r.text
    started = next(p for n, p in events if n == 'GenerationStarted')
    # Some providers may emit an early GenerationCompleted without summary;
    # pick the one that contains result_summary.sampling.
    completed = None
    for n, p in reversed(events):
        rs = p.get('result_summary') or {}
        sampling_block = rs.get('sampling') if rs else None
        if n == 'GenerationCompleted' and sampling_block:
            completed = p
            break
    assert completed, (
        'No GenerationCompleted with sampling in events'
    )
    s_start = started.get('sampling') or {}
    s_comp = (completed.get('result_summary') or {}).get('sampling') or {}
    # Keys we care about
    keys = [
        'requested_max_tokens',
        'effective_max_tokens',
        'cap_applied',
        'cap_source',
    ]
    for k in keys:
        assert s_start.get(k) == s_comp.get(k), (k, s_start, s_comp)
