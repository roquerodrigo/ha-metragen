"""Formato tipado de uma linha retornada pelos endpoints de leituras do Metragen."""

from __future__ import annotations

from typing import TypedDict


class MetragenReadingRow(TypedDict):
    """
    Linha de uma resposta ``LeiturasMorador_Read`` ou ``LeiturasMoradorGas_Read``.

    ``Anterior`` e ``Leitura`` trazem o contador bruto em litros como strings;
    os campos ``*div`` já vêm convertidos para metros cúbicos e BRL.
    """

    Ano: int
    Mes: int
    Medidor: str
    Anterior: str | None
    Leitura: str | None
    Anteriordiv: float | None
    Consumodiv: float | None
    Valordiv: float | None
