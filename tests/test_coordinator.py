from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.metragen.const import DOMAIN
from custom_components.metragen.coordinator import (
    FAILURE_GRACE_PERIOD,
    MetragenDataUpdateCoordinator,
)
from custom_components.metragen.data import MetragenReadings
from custom_components.metragen.exceptions import (
    MetragenApiClientAuthenticationError,
    MetragenApiClientError,
)

from .conftest import COLD_WATER_METER, GAS_METER, HOT_WATER_METER

EMPTY_READINGS = MetragenReadings(water=(), gas=())


@pytest.fixture(autouse=True)
def importer():
    with patch(
        "custom_components.metragen.coordinator.MetragenStatisticsImporter"
    ) as importer_class:
        importer_class.return_value.async_import = AsyncMock()
        yield importer_class


def _make_coordinator(hass, readings=None, scan_interval=timedelta(minutes=5)):
    coord = MetragenDataUpdateCoordinator(hass=hass, scan_interval=scan_interval)
    client = AsyncMock()
    client.async_get_readings = AsyncMock(return_value=readings or EMPTY_READINGS)
    runtime_data = type("D", (), {"client": client})()
    entry = type(
        "E",
        (),
        {"entry_id": "eid", "unique_id": "user", "runtime_data": runtime_data},
    )()
    coord.config_entry = entry
    return coord, client


def test_init_sets_domain_name(hass):
    coord = MetragenDataUpdateCoordinator(
        hass=hass, scan_interval=timedelta(seconds=300)
    )
    assert coord.name == DOMAIN


def test_init_sets_update_interval(hass):
    coord = MetragenDataUpdateCoordinator(
        hass=hass, scan_interval=timedelta(seconds=42)
    )
    assert coord.update_interval == timedelta(seconds=42)


async def test_update_data_keys_meters_by_their_key(hass, sample_readings):
    coord, _ = _make_coordinator(hass, readings=sample_readings)
    result = await coord._async_update_data()
    assert set(result) == {"water_af1234", "water_aq1234", "gas_aq1234"}
    assert result["water_af1234"] is COLD_WATER_METER


async def test_update_data_queries_the_current_year(hass, sample_readings):
    coord, client = _make_coordinator(hass, readings=sample_readings)
    await coord._async_update_data()
    client.async_get_readings.assert_awaited_once_with(dt_util.now().year)


async def test_update_data_falls_back_to_last_year_for_kinds_without_rows(hass):
    coord, client = _make_coordinator(hass)
    client.async_get_readings.side_effect = [
        MetragenReadings(water=(COLD_WATER_METER,), gas=()),
        MetragenReadings(water=(HOT_WATER_METER,), gas=(GAS_METER,)),
    ]
    result = await coord._async_update_data()
    assert set(result) == {"water_af1234", "gas_aq1234"}
    current_year = dt_util.now().year
    assert [call.args[0] for call in client.async_get_readings.await_args_list] == [
        current_year,
        current_year - 1,
    ]


async def test_update_data_returns_empty_payload_when_no_year_has_rows(hass):
    coord, client = _make_coordinator(hass)
    result = await coord._async_update_data()
    assert result == {}
    assert client.async_get_readings.await_count == 2


async def test_update_data_imports_the_history_of_every_meter(
    hass, sample_readings, importer
):
    coord, client = _make_coordinator(hass, readings=sample_readings)
    await coord._async_update_data()
    importer.assert_called_once_with(
        hass=hass,
        client=client,
        current_year=dt_util.now().year,
    )
    imported = list(importer.return_value.async_import.await_args.args[0])
    assert imported == [COLD_WATER_METER, HOT_WATER_METER, GAS_METER]


async def test_update_data_skips_the_history_import_on_failure(
    hass, sample_payload, importer
):
    coord, client = _make_coordinator(hass)
    coord.data = sample_payload
    client.async_get_readings.side_effect = MetragenApiClientError("blip")
    await coord._async_update_data()
    importer.assert_not_called()


async def test_update_data_raises_update_failed_on_api_error(hass):
    coord, client = _make_coordinator(hass)
    client.async_get_readings.side_effect = MetragenApiClientError("down")
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


async def test_update_data_raises_auth_failed_on_auth_error(hass):
    coord, client = _make_coordinator(hass)
    client.async_get_readings.side_effect = MetragenApiClientAuthenticationError("no")
    with pytest.raises(ConfigEntryAuthFailed):
        await coord._async_update_data()


async def test_update_data_serves_last_known_data_within_grace_period(
    hass, sample_payload
):
    coord, client = _make_coordinator(hass)
    coord.data = sample_payload
    client.async_get_readings.side_effect = MetragenApiClientError("blip")
    assert await coord._async_update_data() == sample_payload


async def test_update_data_raises_update_failed_after_grace_period(
    hass, sample_payload
):
    coord, client = _make_coordinator(hass)
    coord.data = sample_payload
    client.async_get_readings.side_effect = MetragenApiClientError("down")
    coord._first_failure_at = (
        dt_util.utcnow() - FAILURE_GRACE_PERIOD - timedelta(seconds=1)
    )
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


async def test_update_data_raises_update_failed_without_previous_data(hass):
    coord, client = _make_coordinator(hass)
    coord.data = None
    client.async_get_readings.side_effect = MetragenApiClientError("down")
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


async def test_update_data_clears_failure_window_after_success(hass, sample_readings):
    coord, _ = _make_coordinator(hass, readings=sample_readings)
    coord._first_failure_at = dt_util.utcnow()
    await coord._async_update_data()
    assert coord._first_failure_at is None


async def test_auth_error_is_not_absorbed_by_the_grace_period(hass, sample_payload):
    coord, client = _make_coordinator(hass)
    coord.data = sample_payload
    client.async_get_readings.side_effect = MetragenApiClientAuthenticationError("no")
    with pytest.raises(ConfigEntryAuthFailed):
        await coord._async_update_data()
