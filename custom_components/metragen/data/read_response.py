"""Envelope tipado da resposta de leitura de um grid Kendo do portal Metragen."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .reading_row import MetragenReadingRow


class MetragenReadResponse(TypedDict):
    """Envelope retornado pelos endpoints ``*_Read``."""

    Data: list[MetragenReadingRow] | None
    Total: int
