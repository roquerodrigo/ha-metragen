"""Long-term statistics import for the monthly history the portal keeps."""

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
    """Return the bucket a reading belongs to: local midnight starting its month."""
    return dt_util.start_of_local_day(reading.period_start)


class MetragenStatisticsImporter:
    """
    Import the monthly readings of every meter as external statistics.

    A sensor state carries the latest reading only, while the portal keeps one
    row per month. Long-term statistics are where Home Assistant stores that
    kind of history: they feed the energy dashboard and the statistics graph
    card. Each meter gets ``metragen:<code>_<kind>`` in cubic meters and
    ``metragen:<code>_<kind>_cost`` in BRL, named like the meter's device so
    the energy dashboard picker reads the same as the device list. The first
    import walks back one year at a time until the portal reports no meters
    at all; later imports only append months newer than the last stored row,
    so a month the portal revises afterwards is never rewritten. The metadata
    is sent on every refresh even without new rows, so the series follow a
    renamed device or a changed language.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: MetragenApiClient,
        current_year: int,
    ) -> None:
        """Bind the importer to the account whose meters it imports."""
        self._hass = hass
        self._client = client
        self._current_year = current_year
        self._readings_by_year: dict[int, MetragenReadings] = {}

    async def async_import(self, meters: Iterable[MetragenMeter]) -> None:
        """Import every meter, postponing the rest when the portal fails."""
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
        """Append the months of one meter that are not stored yet."""
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
        """Collect every month the portal has for the meter, oldest first."""
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
        """Fetch one year from the portal at most once per import run."""
        if year not in self._readings_by_year:
            self._readings_by_year[year] = await self._client.async_get_readings(year)
        return self._readings_by_year[year]

    async def _async_last_row(self, statistic_id: str) -> _LastRow | None:
        """Return the start and running sum of the newest stored row, if any."""
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
        """Build the consumption statistic id of the meter, code first."""
        return f"{DOMAIN}:{slugify(meter.code)}_{meter.kind}"

    def _device_name(self, meter: MetragenMeter) -> str:
        """Name the series like the meter's device, in the configured language."""
        translations = async_get_cached_translations(
            self._hass, self._hass.config.language, "device", DOMAIN
        )
        template = translations.get(
            f"component.{DOMAIN}.device.{meter.device_translation_key}.name",
            "{code}",
        )
        return template.format(code=meter.code)

    def _monthly_cost_name(self) -> str:
        """Return the translated name of the monthly cost sensor."""
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
        """Describe one series to the recorder."""
        return StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=name,
            source=DOMAIN,
            statistic_id=statistic_id,
            unit_class=unit_class,
            unit_of_measurement=unit,
        )
