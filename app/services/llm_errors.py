class MissingAPIKeyError(Exception):
    """Raised when a required provider API key is missing."""


class LLMTimeoutError(Exception):
    """Raised when a provider request times out."""


class LLMProviderError(Exception):
    """Raised for provider-side failures with a safe HTTP status mapping."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code
