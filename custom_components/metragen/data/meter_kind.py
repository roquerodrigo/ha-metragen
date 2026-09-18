"""Insumos que o portal Metragen mede individualmente."""

from __future__ import annotations

from enum import StrEnum


class MetragenMeterKind(StrEnum):
    """Insumo medido por um medidor."""

    WATER = "water"
    GAS = "gas"
