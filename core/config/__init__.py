"""Config subsystem public API (post S1).

Provides:
    get_config() -> AggregatedConfig (schema_version + module refs)
    as_dict()    -> dict representation
    ConfigError  -> raised on validation / unknown key

Specification: see docs/ТЗ/Config-Registry.md
"""

from .loader import (  # noqa: F401
    get_config,
    as_dict,
    ConfigError,
    clear_config_cache,
)


def reset_for_tests() -> None:
    """Backward-compatible test helper.

    Older tests import core.config.reset_for_tests expecting a config state
    reset. The loader already exposes clear_config_cache(); we simply
    delegate to that to avoid editing multiple test files. Kept lightweight
    and intentionally not covered by unit tests (trivial).
    """
    clear_config_cache()


__all__ = [
    "get_config",
    "as_dict",
    "ConfigError",
    "clear_config_cache",
    "reset_for_tests",
]
