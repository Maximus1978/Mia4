"""Pytest configuration ensuring project root is importable.

Adds repository root to sys.path explicitly to avoid interpreter/path quirks.
"""
from __future__ import annotations

import sys
from pathlib import Path
import os
import pytest


@pytest.fixture(autouse=True)
def _isolate_config_env():  # noqa: D401
    """Ensure global config/env side effects do not leak between tests.

    - Clear aggregated config cache between tests
    - Restore MIA_CONFIG_DIR to original value
    """
    from core.config import clear_config_cache  # local import

    prev = os.environ.get("MIA_CONFIG_DIR")
    clear_config_cache()
    try:
        yield
    finally:
        clear_config_cache()
        if prev is None:
            os.environ.pop("MIA_CONFIG_DIR", None)
        else:
            os.environ["MIA_CONFIG_DIR"] = prev


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
