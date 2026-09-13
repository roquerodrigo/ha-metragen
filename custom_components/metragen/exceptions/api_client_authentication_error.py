"""Authentication error raised by the API client."""

from __future__ import annotations

from .api_client_error import MetragenApiClientError


class MetragenApiClientAuthenticationError(
    MetragenApiClientError,
):
    """Exception to indicate an authentication error."""
