from __future__ import annotations

from custom_components.metragen.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_username(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["data"]["username"] == "**REDACTED**"


async def test_diagnostics_redacts_password(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["data"]["password"] == "**REDACTED**"


async def test_diagnostics_includes_entry_metadata(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["domain"] == "metragen"
    assert diag["entry"]["version"] == 1
    assert diag["entry"]["title"] == "**REDACTED**"


async def test_diagnostics_serializes_the_meters(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    cold_water = diag["coordinator_data"]["meter_1"]
    assert cold_water["code"] == "**REDACTED**"
    assert cold_water["kind"] == "water"
    assert cold_water["readings"][-1]["current_reading"] == 86.35


async def test_diagnostics_coordinator_data_none_before_first_refresh(
    hass, setup_integration
):
    setup_integration.runtime_data.coordinator.data = None
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["coordinator_data"] is None


async def test_diagnostics_options_redacted_when_present(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert isinstance(diag["entry"]["options"], dict)


async def test_diagnostics_never_carries_the_meter_code(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert "AF1234" not in repr(diag).upper()
