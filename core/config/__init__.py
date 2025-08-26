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

__all__ = ["get_config", "as_dict", "ConfigError", "clear_config_cache"]
