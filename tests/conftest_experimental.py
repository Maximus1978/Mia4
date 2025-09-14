import os
import pytest


def pytest_runtest_setup(item):  # noqa: D401
    if "experimental" in item.keywords:
        if os.getenv("MIA_ENABLE_EXPERIMENTAL", "0") != "1":
            pytest.skip(
                "experimental tests disabled (set MIA_ENABLE_EXPERIMENTAL=1)"
            )
