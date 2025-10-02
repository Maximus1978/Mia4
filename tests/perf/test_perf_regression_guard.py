import json
from pathlib import Path
import os
import pytest

from core.config.loader import get_config


@pytest.mark.performance
def test_perf_regression_guard():
    """Guardrail test: ensure latest perf_probe run has no regressions.

    This test is lightweight: it only reads the JSON produced by
    scripts/perf_probe.py (not re-running the probe) and asserts no
    regression flags or SLA violations beyond config thresholds.

    Skip conditions:
      - File missing (developer hasn't run probe locally) → skip.
      - Env MIA_PERF_GUARD=0 to disable explicitly.
    """
    if os.getenv("MIA_PERF_GUARD", "1") != "1":
        pytest.skip("Performance guard disabled via MIA_PERF_GUARD")

    path = Path("reports/perf_probe.json")
    if not path.exists():
        pytest.skip(
            "perf_probe.json not found; run scripts/perf_probe.py first"
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    regressions = data.get("regressions", [])
    issues = data.get("issues", [])

    # Load thresholds from config to display (not strictly needed for asserts)
    cfg = get_config()
    thr = cfg.perf.thresholds if cfg.perf else None

    # Assertions: no regressions or SLA issues
    assert not regressions, (
        f"Throughput/latency regressions detected: {regressions}"
    )
    assert not issues, f"SLA issues detected: {issues} (thresholds={thr})"

    # Sanity: at least one short & one long scenario present
    modes = {r.get("mode") for r in data.get("results", [])}
    assert (
        "short" in modes and "long" in modes
    ), "Missing short/long perf scenarios"
