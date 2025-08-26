import os
import pytest
from core import metrics
from core.config import clear_config_cache, get_config


def setup_function(_):
    metrics.reset_for_tests()
    clear_config_cache()


def teardown_function(_):
    for k in [
        'MIA__LLM__PRIMARY__TOP_P',
        'MIA__LLM__PRIMARY__MAX_OUTPUT_TOKENS',
        'MIA__LLM__PRIMARY__N_GPU_LAYERS',
    ]:
        os.environ.pop(k, None)
    clear_config_cache()


def _snapshot_counters():
    return metrics.snapshot()['counters']


def test_invalid_top_p_out_of_range():
    os.environ['MIA__LLM__PRIMARY__TOP_P'] = '1.5'
    with pytest.raises(Exception):
        get_config()
    counters = _snapshot_counters()
    prefix = (
        'config_validation_errors_total{code=config-out-of-range,'
        'path=llm.primary.top_p'
    )
    keys = [k for k in counters if k.startswith(prefix)]
    assert keys, f'Missing metric for top_p: {counters}'


def test_invalid_max_output_tokens_zero():
    os.environ['MIA__LLM__PRIMARY__MAX_OUTPUT_TOKENS'] = '0'
    with pytest.raises(Exception):
        get_config()
    counters = _snapshot_counters()
    prefix = (
        'config_validation_errors_total{code=config-out-of-range,'
        'path=llm.primary.max_output_tokens'
    )
    keys = [k for k in counters if k.startswith(prefix)]
    assert keys, f'Missing metric for max_output_tokens: {counters}'


def test_n_gpu_layers_negative_clipped():
    os.environ['MIA__LLM__PRIMARY__N_GPU_LAYERS'] = '-5'
    cfg = get_config()
    assert cfg.llm.primary.n_gpu_layers == 0
    counters = _snapshot_counters()
    # No error for normalization
    # Only env override metric should exist, no validation error metric
    error_keys = [
        k for k in counters
        if 'n_gpu_layers' in k and k.startswith(
            'config_validation_errors_total'
        )
    ]
    assert not error_keys
