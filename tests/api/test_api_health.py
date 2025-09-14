from fastapi.testclient import TestClient
from mia4.api.app import app


def test_api_health_ok():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_config_mode_env(monkeypatch):
    monkeypatch.setenv("MIA_UI_MODE", "admin")
    client = TestClient(app)
    r = client.get("/config")
    assert r.status_code == 200
    assert r.json()["ui_mode"] == "admin"


def test_api_models_list():
    client = TestClient(app)
    r = client.get("/models")
    assert r.status_code == 200
    data = r.json()
    assert "models" in data and isinstance(data["models"], list)
    # Expect at least primary model present
    assert any(m.get("role") == "primary" for m in data["models"])
