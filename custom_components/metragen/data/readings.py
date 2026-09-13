"""Meters reported by the Metragen portal for one year."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .meter import MetragenMeter


@dataclass(frozen=True)
class MetragenReadings:
    """Water and gas meters reported for the requested year."""

    water: tuple[MetragenMeter, ...]
    gas: tuple[MetragenMeter, ...]
