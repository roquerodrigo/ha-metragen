"""Medidores informados pelo portal Metragen para um ano."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .meter import MetragenMeter


@dataclass(frozen=True)
class MetragenReadings:
    """Medidores de água e de gás informados para o ano solicitado."""

    water: tuple[MetragenMeter, ...]
    gas: tuple[MetragenMeter, ...]
