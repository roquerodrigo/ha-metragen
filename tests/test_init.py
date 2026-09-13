from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.metragen import (
    async_reload_entry,
    async_remove_config_entry_device,
)
from custom_components.metragen.const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN


async def test_setup_entry_loads_successfully(hass, setup_integration):
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_setup_entry_creates_sensors_for_every_meter(
    hass, setup_integration, sample_payload
):
    assert len(hass.states.async_all("sensor")) == len(sample_payload) * 4


async def test_setup_entry_registers_update_listener(hass, setup_integration):
    assert len(setup_integration.update_listeners) == 1


async def test_setup_entry_gives_the_client_a_dedicated_session(
    recorder_mock, hass, mock_api_client, enable_custom_integrations
):
    session = MagicMock()
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "user", "password": "pass"},
        unique_id="user",
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.metragen.async_create_clientsession",
            return_value=session,
        ) as create_session,
        patch("custom_components.metragen.MetragenApiClient") as client_class,
    ):
        client_class.return_value = mock_api_client
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    create_session.assert_called_once_with(hass)
    assert client_class.call_args.kwargs["session"] is session


async def test_unload_entry_succeeds(hass, setup_integration):
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    assert setup_integration.state == ConfigEntryState.NOT_LOADED


async def test_unload_entry_makes_entities_unavailable(hass, setup_integration):
    await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    for state in hass.states.async_all("sensor"):
        assert state.state == "unavailable"


async def test_reload_entry_restores_loaded_state(
    hass, setup_integration, mock_api_client
):
    await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_async_reload_entry_calls_reload(
    hass, setup_integration, mock_api_client
):
    await async_reload_entry(hass, setup_integration)
    await hass.async_block_till_done()
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_runtime_data_populated(hass, setup_integration):
    assert setup_integration.runtime_data.client is not None
    assert setup_integration.runtime_data.coordinator is not None
    assert setup_integration.runtime_data.integration is not None


async def test_scan_interval_defaults_to_const(hass, setup_integration):
    assert setup_integration.runtime_data.coordinator.update_interval == timedelta(
        seconds=DEFAULT_SCAN_INTERVAL_SECONDS
    )


async def test_scan_interval_picks_up_options(
    recorder_mock, hass, mock_api_client, enable_custom_integrations
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "user", "password": "pass"},
        options={CONF_SCAN_INTERVAL: 600},
        unique_id="user",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.coordinator.update_interval == timedelta(seconds=600)


async def test_remove_device_refuses_a_meter_the_portal_lists(hass, setup_integration):
    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, f"{setup_integration.entry_id}_water_af2616")}
    )
    assert device is not None
    assert not await async_remove_config_entry_device(hass, setup_integration, device)


async def test_remove_device_allows_a_meter_the_portal_no_longer_lists(
    hass, setup_integration
):
    stale = dr.async_get(hass).async_get_or_create(
        config_entry_id=setup_integration.entry_id,
        identifiers={(DOMAIN, f"{setup_integration.entry_id}_water_gone")},
    )
    assert await async_remove_config_entry_device(hass, setup_integration, stale)


async def test_remove_device_allows_anything_before_the_first_refresh(
    hass, setup_integration
):
    setup_integration.runtime_data.coordinator.data = None
    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, f"{setup_integration.entry_id}_water_af2616")}
    )
    assert device is not None
    assert await async_remove_config_entry_device(hass, setup_integration, device)
