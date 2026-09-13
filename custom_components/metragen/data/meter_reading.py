"""One monthly reading of a Metragen meter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MetragenMeterReading:
    """Monthly reading of a meter, volumes in cubic meters and cost in BRL."""

    year: int
    month: int
    previous_reading: float
    current_reading: float
    consumption: float
    cost: float

    @property
    def period_start(self) -> date:
        """Return the first day of the month the reading covers."""
        return date(self.year, self.month, 1)
