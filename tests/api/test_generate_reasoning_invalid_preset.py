import os
from pathlib import Path
from fastapi.testclient import TestClient
from mia4.api.app import app
from core.registry.loader import clear_manifest_cache, compute_sha256


def _prep(tmp: Path):
    clear_manifest_cache()
    models_dir = tmp / 'models'
    models_dir.mkdir(exist_ok=True)
    mid = 'modelR'
    mf = models_dir / f'{mid}.bin'
    mf.write_bytes(b'dummy')
    checksum = compute_sha256(mf)
    reg_dir = tmp / 'llm' / 'registry'
    reg_dir.mkdir(parents=True, exist_ok=True)
    reg_dir.joinpath(f'{mid}.yaml').write_text(
        (
            f'id: {mid}\n'
            'family: qwen\n'
            'role: primary\n'
            f'path: models/{mid}.bin\n'
            'context_length: 2048\n'
            'capabilities: [chat]\n'
            f'checksum_sha256: {checksum}\n'
        ),
        encoding='utf-8'
    )
    cfg_dir = tmp / 'configs'
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath('base.yaml').write_text(
        (
            'modules:\n'
            '  enabled: [llm]\n'
            'llm:\n'
            '  primary:\n'
            '    id: modelR\n'
            '    temperature: 0.7\n'
            '    top_p: 0.9\n'
            '    max_output_tokens: 64\n'
            '    n_gpu_layers: 0\n'
            '  reasoning_presets:\n'
            '    low:\n'
            '      temperature: 0.6\n'
            '      top_p: 0.9\n'
            '      reasoning_max_tokens: 8\n'
            '    medium:\n'
            '      temperature: 0.7\n'
            '      top_p: 0.92\n'
            '      reasoning_max_tokens: 24\n'
            '    high:\n'
            '      temperature: 0.85\n'
            '      top_p: 0.95\n'
            '      reasoning_max_tokens: 48\n'
        ),
        encoding='utf-8'
    )
    os.environ['MIA_CONFIG_DIR'] = str(cfg_dir)


def test_invalid_reasoning_preset_returns_400(tmp_path: Path):  # noqa: D401
    _prep(tmp_path)
    client = TestClient(app)
    r = client.post('/generate', json={
        'session_id': 's1',
        'model': 'modelR',
        'prompt': 'test',
        'overrides': {'reasoning_preset': 'off'}
    })
    assert r.status_code == 400
    assert r.json().get('detail') == 'invalid-reasoning-preset'
