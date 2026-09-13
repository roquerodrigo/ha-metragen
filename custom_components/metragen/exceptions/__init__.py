"""Exception classes for the metragen API client."""

from __future__ import annotations

from .api_client_authentication_error import (
    MetragenApiClientAuthenticationError,
)
from .api_client_communication_error import (
    MetragenApiClientCommunicationError,
)
from .api_client_error import MetragenApiClientError

__all__ = [
    "MetragenApiClientAuthenticationError",
    "MetragenApiClientCommunicationError",
    "MetragenApiClientError",
]
