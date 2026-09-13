"""DataUpdateCoordinator for metragen."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER
from .exceptions import (
    MetragenApiClientAuthenticationError,
    MetragenApiClientError,
)
from .statistics import MetragenStatisticsImporter

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant

    from .data import MetragenConfigEntry, MetragenPayload

FAILURE_GRACE_PERIOD = timedelta(hours=24)


class MetragenDataUpdateCoordinator(DataUpdateCoordinator["MetragenPayload"]):
    """Coordinator for fetching the meters and readings from the portal."""

    config_entry: MetragenConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        scan_interval: timedelta,
        config_entry: MetragenConfigEntry | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
            always_update=False,
            config_entry=config_entry,
        )
        self._first_failure_at: datetime | None = None

    async def _async_update_data(self) -> MetragenPayload:
        """Fetch data from the API, tolerating outages shorter than the grace period."""
        current_year = dt_util.now().year
        try:
            payload = await self._fetch_payload(current_year)
        except MetragenApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MetragenApiClientError as exception:
            return self._handle_failure(exception)

        self._first_failure_at = None
        await self._async_import_history(payload, current_year)
        return payload

    async def _fetch_payload(self, current_year: int) -> MetragenPayload:
        """
        Collect the meters of the current year, keyed by meter.

        Readings are published monthly, so early in a year a kind may have no
        rows yet; each kind without rows falls back to the previous year so the
        latest reading keeps being reported across the turn of the year.
        """
        client = self.config_entry.runtime_data.client
        readings = await client.async_get_readings(current_year)
        water, gas = readings.water, readings.gas
        if not water or not gas:
            previous = await client.async_get_readings(current_year - 1)
            water = water or previous.water
            gas = gas or previous.gas
        return {meter.key: meter for meter in (*water, *gas)}

    async def _async_import_history(
        self,
        payload: MetragenPayload,
        current_year: int,
    ) -> None:
        """Push the monthly history of every meter into long-term statistics."""
        importer = MetragenStatisticsImporter(
            hass=self.hass,
            client=self.config_entry.runtime_data.client,
            current_year=current_year,
        )
        await importer.async_import(payload.values())

    def _handle_failure(self, exception: MetragenApiClientError) -> MetragenPayload:
        """
        Serve the last known data while the outage is shorter than the grace period.

        Readings only change once a month, so holding the last known values
        through a portal outage costs nothing in accuracy while keeping every
        entity available for automations and history. A genuine outage still
        surfaces once the window closes, and authentication errors never reach
        here, so re-authentication is prompted at once.
        """
        now = dt_util.utcnow()
        if self._first_failure_at is None:
            self._first_failure_at = now

        last_known_data: MetragenPayload | None = self.data
        if (
            last_known_data is not None
            and now - self._first_failure_at < FAILURE_GRACE_PERIOD
        ):
            LOGGER.warning(
                "Failed to fetch data; serving the last known values: %s", exception
            )
            return last_known_data

        raise UpdateFailed(exception) from exception
