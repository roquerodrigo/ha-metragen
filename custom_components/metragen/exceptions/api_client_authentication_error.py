"""Erro de autenticação levantado pelo cliente da API."""

from __future__ import annotations

from .api_client_error import MetragenApiClientError


class MetragenApiClientAuthenticationError(
    MetragenApiClientError,
):
    """Exceção que indica um erro de autenticação."""
