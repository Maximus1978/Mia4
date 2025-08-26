"""LLM related exception hierarchy."""


class ModelError(Exception):
    """Base model exception."""


class ModelLoadError(ModelError):
    """Raised when model cannot be loaded.

    Typical reasons: missing file, checksum mismatch, runtime init failure.
    """


class ModelGenerationError(ModelError):
    """Raised when text generation fails.

    Reasons: runtime error, user cancellation, timeout.
    """
