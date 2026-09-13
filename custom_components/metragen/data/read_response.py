"""Typed envelope of a Kendo grid read response from the Metragen portal."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .reading_row import MetragenReadingRow


class MetragenReadResponse(TypedDict):
    """Envelope returned by the ``*_Read`` endpoints."""

    Data: list[MetragenReadingRow] | None
    Total: int
