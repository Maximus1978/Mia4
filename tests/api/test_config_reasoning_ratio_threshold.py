from fastapi.testclient import TestClient
from mia4.api.app import app
from core.config import get_config


def test_config_reasoning_ratio_threshold_round_trip():
    client = TestClient(app)
    resp = client.get('/config')
    assert resp.status_code == 200
    data = resp.json()
    ui_val = data.get('reasoning_ratio_threshold')
    assert isinstance(
        ui_val, (int, float)
    ), 'UI threshold missing or not numeric'
    cfg = get_config()
    # Navigate path llm.postproc.reasoning.ratio_alert_threshold
    llm_conf = getattr(cfg, 'llm')
    postproc = getattr(llm_conf, 'postproc')
    reasoning = (
        postproc.get('reasoning')
        if isinstance(postproc, dict)
        else getattr(postproc, 'reasoning')
    )
    if isinstance(reasoning, dict):
        backend_val = reasoning.get('ratio_alert_threshold')
    else:
        backend_val = getattr(reasoning, 'ratio_alert_threshold')
    assert (
        abs(float(ui_val) - float(backend_val)) < 1e-9
    ), 'Mismatch between /config and backend value'
    # Guard acceptable range (UI clamp contract)
    assert 0.01 <= float(ui_val) <= 0.99, 'Threshold out of broad sanity range'
