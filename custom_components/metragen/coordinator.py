"""DataUpdateCoordinator do metragen."""

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
    """Coordinator que busca os medidores e as leituras no portal."""

    config_entry: MetragenConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        scan_interval: timedelta,
        config_entry: MetragenConfigEntry | None = None,
    ) -> None:
        """Inicializa."""
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
        """Busca os dados da API, tolerando quedas mais curtas que a carência."""
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
        Reúne os medidores do ano corrente, indexados por medidor.

        As leituras são publicadas mensalmente, então no começo do ano um tipo
        pode ainda não ter linhas; cada tipo sem linhas recai no ano anterior,
        para que a leitura mais recente continue sendo informada na virada do
        ano.
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
        """Envia o histórico mensal de cada medidor às estatísticas de longo prazo."""
        importer = MetragenStatisticsImporter(
            hass=self.hass,
            client=self.config_entry.runtime_data.client,
            current_year=current_year,
        )
        await importer.async_import(payload.values())

    def _handle_failure(self, exception: MetragenApiClientError) -> MetragenPayload:
        """
        Serve os últimos dados conhecidos enquanto a queda é menor que a carência.

        As leituras só mudam uma vez por mês, então manter os últimos valores
        conhecidos durante uma queda do portal não custa nada em precisão e
        mantém todas as entidades disponíveis para automações e histórico. Uma
        queda de verdade ainda aparece quando a janela se encerra, e erros de
        autenticação nunca chegam aqui, então a reautenticação é pedida na hora.
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
