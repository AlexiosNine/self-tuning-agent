"""Custom exceptions for self-tuning-agent."""


class SelfTuningAgentError(Exception):
    """Base exception for all self-tuning-agent errors."""


class VersionNotFoundError(SelfTuningAgentError):
    """Raised when a strategy version does not exist."""


class VersionAlreadyExistsError(SelfTuningAgentError):
    """Raised when attempting to create a version that already exists."""


class InvalidVersionStateError(SelfTuningAgentError):
    """Raised when a version is in an invalid state for the requested operation."""


class FileOperationError(SelfTuningAgentError):
    """Raised when a file system operation fails."""


class ProviderError(SelfTuningAgentError):
    """Raised when an LLM provider call fails."""
