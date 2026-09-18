"""Importação do histórico mensal do portal para as estatísticas de longo prazo."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.translation import async_get_cached_translations
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify
from homeassistant.util.unit_conversion import VolumeConverter

from .const import CURRENCY_BRAZILIAN_REAL, DOMAIN, LOGGER
from .exceptions import MetragenApiClientError

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from homeassistant.core import HomeAssistant

    from .api import MetragenApiClient
    from .data import MetragenMeter, MetragenMeterReading, MetragenReadings

MAX_HISTORY_YEARS = 10

type _MonthKey = tuple[int, int]
type _LastRow = tuple[datetime, float]


def _period_start(reading: MetragenMeterReading) -> datetime:
    """Retorna o bucket da leitura: a meia-noite local que inicia o mês dela."""
    return dt_util.start_of_local_day(reading.period_start)


class MetragenStatisticsImporter:
    """
    Importa as leituras mensais de cada medidor como estatísticas externas.

    O estado de um sensor traz só a leitura mais recente, enquanto o portal
    guarda uma linha por mês. É nas estatísticas de longo prazo que o Home
    Assistant armazena esse tipo de histórico: elas alimentam o painel de
    energia e o card de gráfico de estatísticas. Cada medidor recebe
    ``metragen:<code>_<kind>`` em metros cúbicos e
    ``metragen:<code>_<kind>_cost`` em BRL, com o mesmo nome do dispositivo do
    medidor, para que o seletor do painel de energia leia igual à lista de
    dispositivos. A primeira importação volta um ano de cada vez até o portal
    não informar nenhum medidor; as seguintes só acrescentam meses mais novos
    que a última linha armazenada, então um mês que o portal revise depois
    nunca é reescrito. Os metadados são enviados a cada atualização, mesmo sem
    linhas novas, para que as séries acompanhem um dispositivo renomeado ou
    uma troca de idioma.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: MetragenApiClient,
        current_year: int,
    ) -> None:
        """Vincula o importador à conta cujos medidores ele importa."""
        self._hass = hass
        self._client = client
        self._current_year = current_year
        self._readings_by_year: dict[int, MetragenReadings] = {}

    async def async_import(self, meters: Iterable[MetragenMeter]) -> None:
        """Importa cada medidor, adiando o restante quando o portal falha."""
        for meter in meters:
            try:
                await self._async_import_meter(meter)
            except MetragenApiClientError as exception:
                LOGGER.warning(
                    "Failed to fetch the reading history of meter %s, "
                    "retrying on the next refresh: %s",
                    meter.code,
                    exception,
                )
                return

    async def _async_import_meter(self, meter: MetragenMeter) -> None:
        """Acrescenta os meses de um medidor que ainda não estão armazenados."""
        consumption_id = self._series_id(meter)
        cost_id = f"{consumption_id}_cost"
        last_consumption = await self._async_last_row(consumption_id)
        last_cost = await self._async_last_row(cost_id)

        if last_consumption is None:
            readings = await self._async_full_history(meter)
            consumption_sum = 0.0
            cost_sum = 0.0
        else:
            last_start, consumption_sum = last_consumption
            cost_sum = 0.0 if last_cost is None else last_cost[1]
            readings = [
                reading
                for reading in meter.readings
                if _period_start(reading) > last_start
            ]

        consumption_rows: list[StatisticData] = []
        cost_rows: list[StatisticData] = []
        for reading in readings:
            start = _period_start(reading)
            consumption_sum += reading.consumption
            cost_sum += reading.cost
            consumption_rows.append(
                StatisticData(
                    start=start,
                    state=reading.current_reading,
                    sum=round(consumption_sum, 3),
                ),
            )
            cost_rows.append(
                StatisticData(start=start, state=reading.cost, sum=round(cost_sum, 2)),
            )

        if readings:
            LOGGER.debug(
                "Importing %d months of statistics for meter %s",
                len(readings),
                meter.code,
            )
        device_name = self._device_name(meter)
        async_add_external_statistics(
            self._hass,
            self._metadata(
                consumption_id,
                device_name,
                unit_class=VolumeConverter.UNIT_CLASS,
                unit=UnitOfVolume.CUBIC_METERS,
            ),
            consumption_rows,
        )
        async_add_external_statistics(
            self._hass,
            self._metadata(
                cost_id,
                f"{device_name} {self._monthly_cost_name()}",
                unit_class=None,
                unit=CURRENCY_BRAZILIAN_REAL,
            ),
            cost_rows,
        )

    async def _async_full_history(
        self,
        meter: MetragenMeter,
    ) -> list[MetragenMeterReading]:
        """Reúne todos os meses que o portal tem do medidor, em ordem cronológica."""
        readings_by_month: dict[_MonthKey, MetragenMeterReading] = {
            (reading.year, reading.month): reading for reading in meter.readings
        }
        first_year = self._current_year - 1
        for year in range(first_year, first_year - MAX_HISTORY_YEARS, -1):
            readings = await self._async_readings_of(year)
            if not readings.water and not readings.gas:
                break
            for candidate in (*readings.water, *readings.gas):
                if candidate.key == meter.key:
                    readings_by_month.update(
                        {(r.year, r.month): r for r in candidate.readings},
                    )
        return [readings_by_month[month] for month in sorted(readings_by_month)]

    async def _async_readings_of(self, year: int) -> MetragenReadings:
        """Busca um ano no portal no máximo uma vez por execução da importação."""
        if year not in self._readings_by_year:
            self._readings_by_year[year] = await self._client.async_get_readings(year)
        return self._readings_by_year[year]

    async def _async_last_row(self, statistic_id: str) -> _LastRow | None:
        """Retorna o início e a soma acumulada da última linha armazenada, se houver."""
        rows = await get_instance(self._hass).async_add_executor_job(
            partial(
                get_last_statistics,
                self._hass,
                1,
                statistic_id,
                convert_units=True,
                types={"sum"},
            ),
        )
        if not rows:
            return None
        last_row = rows[statistic_id][0]
        return dt_util.utc_from_timestamp(last_row["start"]), last_row["sum"] or 0.0

    def _series_id(self, meter: MetragenMeter) -> str:
        """Monta o id da estatística de consumo do medidor, com o código primeiro."""
        return f"{DOMAIN}:{slugify(meter.code)}_{meter.kind}"

    def _device_name(self, meter: MetragenMeter) -> str:
        """Nomeia a série como o dispositivo do medidor, no idioma configurado."""
        translations = async_get_cached_translations(
            self._hass, self._hass.config.language, "device", DOMAIN
        )
        template = translations.get(
            f"component.{DOMAIN}.device.{meter.device_translation_key}.name",
            "{code}",
        )
        return template.format(code=meter.code)

    def _monthly_cost_name(self) -> str:
        """Retorna o nome traduzido do sensor de valor mensal."""
        translations = async_get_cached_translations(
            self._hass, self._hass.config.language, "entity", DOMAIN
        )
        return translations.get(
            f"component.{DOMAIN}.entity.sensor.monthly_cost.name", "cost"
        )

    def _metadata(
        self,
        statistic_id: str,
        name: str,
        *,
        unit_class: str | None,
        unit: str,
    ) -> StatisticMetaData:
        """Descreve uma série para o recorder."""
        return StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=name,
            source=DOMAIN,
            statistic_id=statistic_id,
            unit_class=unit_class,
            unit_of_measurement=unit,
        )
