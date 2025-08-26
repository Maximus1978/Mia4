import pytest
from core.errors import validate_error_type


def test_error_taxonomy_known():
    assert validate_error_type("provider-error") == "provider-error"
    assert validate_error_type("config-out-of-range") == "config-out-of-range"
    assert validate_error_type("config-invalid") == "config-invalid"


def test_error_taxonomy_unknown():
    with pytest.raises(AssertionError):
        validate_error_type("not-a-code")
