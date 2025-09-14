from fastapi.testclient import TestClient
from core.events import on, reset_listeners_for_tests
from mia4.api.app import app
import os


def _set_env_config(cfg_dir):  # helper to set env temporarily
    prev = os.environ.get("MIA_CONFIG_DIR")
    os.environ["MIA_CONFIG_DIR"] = str(cfg_dir)
    return prev


def _configure(tmp_path):
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir(exist_ok=True)
    cfg_dir.joinpath("base.yaml").write_text(
        (
            "llm:\n"
            "  primary:\n"
            "    id: presetModel\n"
            "    temperature: 0.5\n"
            "    top_p: 0.8\n"
            "    max_output_tokens: 64\n"
            "  reasoning_presets:\n"
            "    low:\n"
            "      reasoning_max_tokens: 4\n"
            "      temperature: 0.7\n"
            "      top_p: 0.9\n"
            "  postproc:\n"
            "    enabled: true\n"
            "    reasoning:\n"
            "      max_tokens: 8\n"
            "      drop_from_history: true\n"
        ),
        encoding="utf-8",
    )
    return cfg_dir


def test_reasoning_preset_applied_baseline(tmp_path):
    cfg_dir = _configure(tmp_path)
    prev = _set_env_config(cfg_dir)
    events = []
    on(lambda n, p: events.append((n, p)))
    client = TestClient(app)
    r = client.post(
        "/generate",
        json={
            "session_id": "s1",
            "model": "presetModel",
            "prompt": "Hello",
            "overrides": {"reasoning_preset": "low"},
            "stream": False,
        },
    )
    assert r.status_code == 200
    names = [n for n, _ in events]
    assert "ReasoningPresetApplied" in names
    payloads = [p for n, p in events if n == "ReasoningPresetApplied"]
    assert payloads
    ev = payloads[0]
    assert ev["preset"] == "low"
    assert ev["mode"] == "baseline"
    assert ev.get("overridden_fields") is None
    if prev is None:
        os.environ.pop("MIA_CONFIG_DIR", None)
    else:
        os.environ["MIA_CONFIG_DIR"] = prev


def test_reasoning_preset_applied_overridden(tmp_path):
    cfg_dir = _configure(tmp_path)
    prev = _set_env_config(cfg_dir)
    events = []
    on(lambda n, p: events.append((n, p)))
    client = TestClient(app)
    r = client.post(
        "/generate",
        json={
            "session_id": "s1",
            "model": "presetModel",
            "prompt": "Hello",
            "overrides": {"reasoning_preset": "low", "temperature": 0.2},
            "stream": False,
        },
    )
    assert r.status_code == 200
    payloads = [p for n, p in events if n == "ReasoningPresetApplied"]
    assert payloads
    ev = payloads[0]
    assert ev["preset"] == "low"
    assert ev["mode"] == "overridden"
    assert "temperature" in (ev.get("overridden_fields") or [])
    reset_listeners_for_tests()
    if prev is None:
        os.environ.pop("MIA_CONFIG_DIR", None)
    else:
        os.environ["MIA_CONFIG_DIR"] = prev
