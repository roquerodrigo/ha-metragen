"""Utilities the Metragen portal meters individually."""

from __future__ import annotations

from enum import StrEnum


class MetragenMeterKind(StrEnum):
    """Utility measured by a meter."""

    WATER = "water"
    GAS = "gas"
