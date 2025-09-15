from fastapi.testclient import TestClient

from mia4.api.app import app


def test_api_presets_endpoint_ok():  # noqa: D401
    client = TestClient(app)
    r = client.get("/presets")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("reasoning_presets"), dict)
    # expect standard keys present
    rp = data["reasoning_presets"]
    assert set(rp.keys()) >= {"low", "medium", "high"}
