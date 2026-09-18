"""Uma leitura mensal de um medidor Metragen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MetragenMeterReading:
    """Leitura mensal de um medidor, volumes em metros cúbicos e valor em BRL."""

    year: int
    month: int
    previous_reading: float
    current_reading: float
    consumption: float
    cost: float

    @property
    def period_start(self) -> date:
        """Retorna o primeiro dia do mês que a leitura cobre."""
        return date(self.year, self.month, 1)
