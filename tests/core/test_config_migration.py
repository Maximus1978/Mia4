import importlib
import os
import tempfile
from pathlib import Path


def _with_temp_config(yaml_text: str):
    prev = os.environ.get("MIA_CONFIG_DIR")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "base.yaml").write_text(yaml_text, encoding="utf-8")
        os.environ["MIA_CONFIG_DIR"] = str(tmp)
        import core.config.loader as loader
        importlib.reload(loader)
        clear_fn = getattr(loader, "clear_config_cache", None)
        if clear_fn:
            clear_fn()
        yield loader
    if prev is None:
        os.environ.pop("MIA_CONFIG_DIR", None)
    else:
        os.environ["MIA_CONFIG_DIR"] = prev


def test_migration_adds_schema_version_and_modules():
    legacy_yaml = (
        "llm:\n"
        "  primary: {id: p}\n"
        "  lightweight: {id: l}\n"
        "embeddings: {main: {id: e1}, fallback: {id: e2}}\n"
        "rag: {collection_default: memory, hybrid: {}, normalize: {}}\n"
        "emotion: {model: {id: emo}, fsm: {hysteresis_ms: 1000}}\n"
        "reflection: {schedule: {cron: '0 3 * * *'}}\n"
        "metrics: {}\n"
        "logging: {}\n"
        "storage: {}\n"
        "system: {}\n"
    )
    for loader in _with_temp_config(legacy_yaml):
        cfg = loader.get_config()
        assert cfg.schema_version == 1
        assert "llm" in cfg.modules.enabled
        assert cfg.llm.primary.id == "p"
