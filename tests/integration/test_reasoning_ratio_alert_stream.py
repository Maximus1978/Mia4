from core import metrics
from core.config import get_config
from src.mia4.api.routes.generate import _record_reasoning_ratio_alert


def test_reasoning_ratio_alert_stream():  # simplified integration
    cfg = get_config()
    model_id = cfg.llm.primary.id
    metrics.reset_for_tests()
    try:
        threshold = cfg.llm.postproc.get("reasoning", {}).get(
            "ratio_alert_threshold", 0.45
        )
    except Exception:  # noqa: BLE001
        threshold = 0.45
    _record_reasoning_ratio_alert(model_id, threshold - 0.05, cfg.llm)
    _record_reasoning_ratio_alert(model_id, threshold + 0.10, cfg.llm)
    snap = metrics.snapshot()["counters"]
    below = sum(
        v
        for k, v in snap.items()
        if k.startswith("reasoning_ratio_alert_total") and "bucket=below" in k
    )
    above = sum(
        v
        for k, v in snap.items()
        if k.startswith("reasoning_ratio_alert_total") and "bucket=above" in k
    )
    assert below >= 1 and above >= 1, snap
