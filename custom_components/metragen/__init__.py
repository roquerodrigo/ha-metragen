"""Integração Metragen para o Home Assistant."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, cast

from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import MetragenApiClient
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN
from .coordinator import MetragenDataUpdateCoordinator
from .data import MetragenData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry

    from .data import MetragenConfigData, MetragenConfigEntry, MetragenPayload

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MetragenConfigEntry,
) -> bool:
    """Configura o Metragen a partir de uma config entry."""
    config = cast("MetragenConfigData", entry.data)
    scan_interval_seconds: int = int(
        entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
    )
    coordinator = MetragenDataUpdateCoordinator(
        hass=hass,
        scan_interval=timedelta(seconds=scan_interval_seconds),
        config_entry=entry,
    )
    # O portal autentica por cookies de sessão, então a entry precisa de uma
    # sessão com cookie jar próprio em vez da compartilhada; o Home Assistant a
    # desvincula quando a entry é descarregada.
    entry.runtime_data = MetragenData(
        client=MetragenApiClient(
            username=config["username"],
            password=config["password"],
            session=async_create_clientsession(hass),
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: MetragenConfigEntry,
) -> bool:
    """Trata a remoção de uma entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: MetragenConfigEntry,
) -> None:
    """Recarrega a config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant,  # noqa: ARG001 -- parte da assinatura que o Home Assistant chama
    entry: MetragenConfigEntry,
    device_entry: DeviceEntry,
) -> bool:
    """Permite excluir medidores que o portal não lista mais para esta conta."""
    payload: MetragenPayload | None = entry.runtime_data.coordinator.data
    listed_identifiers = {
        (DOMAIN, f"{entry.entry_id}_{meter_key}") for meter_key in (payload or {})
    }
    return not (listed_identifiers & device_entry.identifiers)
