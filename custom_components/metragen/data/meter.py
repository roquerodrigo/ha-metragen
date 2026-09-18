"""Um medidor Metragen e as leituras que o portal informa para ele."""

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
    """Medidor identificado pelo código do portal, com leituras em ordem cronológica."""

    kind: MetragenMeterKind
    code: str
    readings: tuple[MetragenMeterReading, ...]

    @property
    def key(self) -> str:
        """Retorna o identificador que permanece estável entre atualizações."""
        return f"{self.kind}_{slugify(self.code)}"

    @property
    def latest(self) -> MetragenMeterReading | None:
        """Retorna a leitura mais recente, se o portal informou alguma."""
        return self.readings[-1] if self.readings else None

    @property
    def yearly_consumption(self) -> float:
        """Retorna o consumo acumulado no ano da leitura mais recente."""
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
        Retorna a chave de tradução que nomeia o que o medidor mede.

        A medição individualizada rotula os medidores com um prefixo para água
        quente (``AQ``) e água fria (``AF``); qualquer outro código recai no
        tipo puro.
        """
        if self.kind is MetragenMeterKind.GAS:
            return "gas_meter"
        code = self.code.upper()
        if code.startswith(_HOT_WATER_CODE_PREFIX):
            return "hot_water_meter"
        if code.startswith(_COLD_WATER_CODE_PREFIX):
            return "cold_water_meter"
        return "water_meter"
