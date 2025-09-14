import pytest

# Obsolete test module: synthetic forced cutover & marker-missing heuristics
# removed per developer spec (no artificial reasoning fabrication).
# Entire module skipped to avoid legacy expectations.
pytest.skip(
    (
        "forced cutover logic removed: synthetic reasoning disabled; test "
        "deprecated"
    ),
    allow_module_level=True,
)
