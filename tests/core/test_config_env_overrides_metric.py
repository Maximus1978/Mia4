import os
from core.config import clear_config_cache, as_dict
from core import metrics


def test_env_override_metric_and_logging(capsys):
    metrics.reset_for_tests()
    clear_config_cache()
    os.environ['MIA__LLM__PRIMARY__TEMPERATURE'] = '1.5'
    try:
        cfg = as_dict()  # triggers load with env
        assert cfg['llm']['primary']['temperature'] == 1.5
        snap = metrics.snapshot()
        counters = snap['counters']
        matched = [
            k for k in counters
            if k.startswith('env_override_total{path=llm.primary.temperature')
        ]
        assert matched, (
            'No env_override_total counter for llm.primary.temperature'
        )
        # stdout log presence
        out = capsys.readouterr().out
        assert 'config-env-override' in out
        assert 'path=llm.primary.temperature' in out
    finally:
        # cleanup env
        del os.environ['MIA__LLM__PRIMARY__TEMPERATURE']
        clear_config_cache()
