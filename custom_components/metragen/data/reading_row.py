"""Typed shape of one row returned by the Metragen readings endpoints."""

from __future__ import annotations

from typing import TypedDict


class MetragenReadingRow(TypedDict):
    """
    Row of a ``LeiturasMorador_Read`` or ``LeiturasMoradorGas_Read`` response.

    ``Anterior`` and ``Leitura`` carry the raw counter in liters as strings;
    the ``*div`` fields are already scaled to cubic meters and BRL.
    """

    Ano: int
    Mes: int
    Medidor: str
    Anterior: str | None
    Leitura: str | None
    Anteriordiv: float | None
    Consumodiv: float | None
    Valordiv: float | None
