"""Domain exceptions for autocomplete providers."""

from typing import Optional


class AutocompleteError(Exception):
    """Base exception for all autocomplete provider errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NetworkError(AutocompleteError):
    """Base exception for connectivity and socket errors."""
    pass


class NetworkTimeoutError(NetworkError):
    """Raised when connection or read timeout occurs."""
    pass


class NetworkConnectionError(NetworkError):
    """Raised on DNS failure, connection refusal, or network disconnect."""
    pass


class AccessForbiddenError(AutocompleteError):
    """Raised when the provider rejects access with HTTP 403 (unauthorized/forbidden)."""

    def __init__(self, message: str = "Access forbidden by autocomplete provider (HTTP 403).") -> None:
        super().__init__(message, status_code=403)


class RateLimitError(AutocompleteError):
    """Raised when the provider returns HTTP 429 Too Many Requests."""

    def __init__(
        self,
        message: str = "Rate limit exceeded by autocomplete provider (HTTP 429).",
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ProviderUnavailableError(AutocompleteError):
    """Raised on HTTP 5xx server errors from the provider."""
    pass


class MalformedResponseError(AutocompleteError):
    """Raised when provider returns an unparseable or unexpected response payload."""
    pass


class OperationCancelledError(AutocompleteError):
    """Raised when an in-flight autocomplete request is cancelled."""

    def __init__(self, message: str = "Autocomplete operation was cancelled.") -> None:
        super().__init__(message)
