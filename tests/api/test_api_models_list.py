from fastapi.testclient import TestClient
from mia4.api.app import app


def test_api_models_list():
    client = TestClient(app)
    r = client.get("/models")
    assert r.status_code == 200
    data = r.json()
    assert "models" in data
    assert any(m.get("id") for m in data["models"]), "No models returned"
    # Each model should expose flags + passport key (passport may be None)
    for m in data["models"]:
        assert "flags" in m
        assert "stub" in m["flags"], "stub flag missing"
        assert "passport" in m
        # system_prompt placeholder present
        assert "system_prompt" in m
