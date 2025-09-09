from core import metrics
from mia4.api.routes.generate import _record_reasoning_ratio_alert


class DummyLLMConf:
    def __init__(self, threshold: float):
        self.postproc = {"reasoning": {"ratio_alert_threshold": threshold}}


def test_reasoning_ratio_alert_metric_buckets():
    metrics.reset_for_tests()
    conf = DummyLLMConf(0.5)
    _record_reasoning_ratio_alert("m1", 0.40, conf)  # below
    _record_reasoning_ratio_alert("m1", 0.75, conf)  # above
    snap = metrics.snapshot()["counters"]
    # Expect both buckets present
    assert any(
        k.startswith("reasoning_ratio_alert_total") and "bucket=below" in k
        for k in snap
    )
    assert any(
        k.startswith("reasoning_ratio_alert_total") and "bucket=above" in k
        for k in snap
    )
