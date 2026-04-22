import pytest

from src.common.exceptions import (
    FileOperationError,
    InvalidVersionStateError,
    ProviderError,
    SelfTuningAgentError,
    VersionAlreadyExistsError,
    VersionNotFoundError,
)


def test_exception_hierarchy():
    """Verify all exceptions inherit from base."""
    exceptions = [
        VersionNotFoundError,
        VersionAlreadyExistsError,
        InvalidVersionStateError,
        FileOperationError,
        ProviderError,
    ]

    for exc_class in exceptions:
        assert issubclass(exc_class, SelfTuningAgentError)
        assert issubclass(exc_class, Exception)


def test_exceptions_can_be_raised():
    """Verify exceptions can be raised with messages."""
    with pytest.raises(VersionNotFoundError, match="v001"):
        raise VersionNotFoundError("Version v001 not found")

    with pytest.raises(ProviderError, match="API"):
        raise ProviderError("API call failed")


def test_exceptions_can_be_caught_by_base():
    """Verify base exception catches all subclasses."""
    try:
        raise VersionNotFoundError("test")
    except SelfTuningAgentError:
        pass  # Should catch it
    else:
        pytest.fail("Base exception should catch subclass")
