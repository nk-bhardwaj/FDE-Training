class MissingAPIKeyError(Exception):
    """Raised when a required provider API key is missing."""


class LLMTimeoutError(Exception):
    """Raised when a provider request times out."""


class LLMProviderError(Exception):
    """Raised for provider-side failures with a safe HTTP status mapping."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class ToolCallLimitError(LLMProviderError):
    """Raised when the tool-calling loop exceeds the iteration limit."""

    def __init__(self, message: str = "Exceeded maximum tool-calling iterations") -> None:
        super().__init__(message, status_code=502)
