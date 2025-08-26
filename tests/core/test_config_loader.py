import os
import tempfile
import importlib
from pathlib import Path

import pytest


def _with_temp_config(yaml_text: str):
    prev = os.environ.get("MIA_CONFIG_DIR")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "base.yaml").write_text(yaml_text, encoding="utf-8")
        os.environ["MIA_CONFIG_DIR"] = str(tmp)
        import core.config.loader as loader
        importlib.reload(loader)
        # Clear any previous cached config (if function exists)
        clear_fn = getattr(loader, "clear_config_cache", None)
        if clear_fn:
            clear_fn()
        yield loader
    # restore env var
    if prev is None:
        os.environ.pop("MIA_CONFIG_DIR", None)
    else:
        os.environ["MIA_CONFIG_DIR"] = prev


def test_valid_load():
    yaml_content_valid = (
        "llm:\n"
        "  primary:\n"
        "    id: test-primary\n"
        "  lightweight:\n"
        "    id: test-light\n"
        "embeddings:\n"
        "  main:\n"
        "    id: emb-main\n"
        "  fallback:\n"
        "    id: emb-fb\n"
        "rag:\n"
        "  collection_default: memory\n"
        "  hybrid: {}\n"
        "  normalize: {}\n"
        "emotion:\n"
        "  model: { id: emo }\n"
        "  fsm: { hysteresis_ms: 1000 }\n"
        "reflection: { schedule: { cron: '0 3 * * *' } }\n"
        "metrics: {}\n"
        "logging: {}\n"
        "storage: {}\n"
        "system: {}\n"
    )
    for loader in _with_temp_config(yaml_content_valid):
        cfg = loader.get_config()
        assert cfg.llm.primary.id == "test-primary"


def test_invalid_key_rejected():
    yaml_content_invalid = (
        "llm:\n"
        "  primary:\n"
        "    id: test-primary\n"
        "  lightweight:\n"
        "    id: test-light\n"
        "  unknown_field: 123\n"
        "embeddings:\n"
        "  main:\n"
        "    id: emb-main\n"
        "  fallback:\n"
        "    id: emb-fb\n"
        "rag:\n"
        "  collection_default: memory\n"
        "  hybrid: {}\n"
        "  normalize: {}\n"
        "emotion:\n"
        "  model: { id: emo }\n"
        "  fsm: { hysteresis_ms: 1000 }\n"
        "reflection: { schedule: { cron: '0 3 * * *' } }\n"
        "metrics: {}\n"
        "logging: {}\n"
        "storage: {}\n"
        "system: {}\n"
    )
    for loader in _with_temp_config(yaml_content_invalid):
        with pytest.raises(Exception):
            loader.get_config()
