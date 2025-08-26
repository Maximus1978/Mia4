import pytest
from core.errors import validate_error_type


def test_error_taxonomy_known():
    assert validate_error_type("provider-error") == "provider-error"


def test_error_taxonomy_unknown():
    with pytest.raises(AssertionError):
        validate_error_type("not-a-code")
