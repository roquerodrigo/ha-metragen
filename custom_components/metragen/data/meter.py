"""A Metragen meter and the readings the portal reports for it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.util import slugify

from .meter_kind import MetragenMeterKind

if TYPE_CHECKING:
    from .meter_reading import MetragenMeterReading

_HOT_WATER_CODE_PREFIX = "AQ"
_COLD_WATER_CODE_PREFIX = "AF"


@dataclass(frozen=True)
class MetragenMeter:
    """Meter identified by its portal code, with readings in chronological order."""

    kind: MetragenMeterKind
    code: str
    readings: tuple[MetragenMeterReading, ...]

    @property
    def key(self) -> str:
        """Return the identifier that stays stable across refreshes."""
        return f"{self.kind}_{slugify(self.code)}"

    @property
    def latest(self) -> MetragenMeterReading | None:
        """Return the most recent reading, if the portal reported any."""
        return self.readings[-1] if self.readings else None

    @property
    def yearly_consumption(self) -> float:
        """Return the consumption accumulated in the year of the latest reading."""
        latest = self.latest
        if latest is None:
            return 0.0
        return round(
            sum(
                reading.consumption
                for reading in self.readings
                if reading.year == latest.year
            ),
            3,
        )

    @property
    def device_translation_key(self) -> str:
        """
        Return the translation key naming what the meter measures.

        Brazilian individualized metering labels meters with a prefix for hot
        (``AQ``, água quente) and cold (``AF``, água fria) water; anything else
        falls back to the plain kind.
        """
        if self.kind is MetragenMeterKind.GAS:
            return "gas_meter"
        code = self.code.upper()
        if code.startswith(_HOT_WATER_CODE_PREFIX):
            return "hot_water_meter"
        if code.startswith(_COLD_WATER_CODE_PREFIX):
            return "cold_water_meter"
        return "water_meter"
