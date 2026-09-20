from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.util import dt as dt_util

from custom_components.metragen.data import (
    MetragenMeter,
    MetragenMeterKind,
    MetragenMeterReading,
    MetragenReadings,
)

if TYPE_CHECKING:
    from collections.abc import Generator

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def mock_recorder_before_hass(async_test_recorder) -> None:
    """Resolve o banco do recorder antes de a fixture hass iniciar."""


def make_reading(
    year: int,
    month: int,
    current: float,
    consumption: float,
    cost: float = 0.0,
) -> MetragenMeterReading:
    return MetragenMeterReading(
        year=year,
        month=month,
        previous_reading=round(current - consumption, 3),
        current_reading=current,
        consumption=consumption,
        cost=cost,
    )


COLD_WATER_METER = MetragenMeter(
    kind=MetragenMeterKind.WATER,
    code="AF1234",
    readings=(
        make_reading(2026, 6, 80.25, 7.5, 120.456),
        make_reading(2026, 7, 86.35, 6.1, 96.432),
    ),
)
HOT_WATER_METER = MetragenMeter(
    kind=MetragenMeterKind.WATER,
    code="AQ1234",
    readings=(
        make_reading(2026, 6, 33.65, 5.2),
        make_reading(2026, 7, 39.15, 5.5),
    ),
)
GAS_METER = MetragenMeter(
    kind=MetragenMeterKind.GAS,
    code="AQ1234",
    readings=(
        make_reading(2026, 4, 24.15, 3.05, 25.41237),
        make_reading(2026, 5, 28.45, 4.3, 140.98765),
    ),
)


@pytest.fixture
def sample_readings() -> MetragenReadings:
    return MetragenReadings(
        water=(COLD_WATER_METER, HOT_WATER_METER),
        gas=(GAS_METER,),
    )


@pytest.fixture
def sample_payload(sample_readings: MetragenReadings) -> dict[str, MetragenMeter]:
    return {
        meter.key: meter for meter in (*sample_readings.water, *sample_readings.gas)
    }


@pytest.fixture
def mock_api_client(sample_readings: MetragenReadings) -> Generator:
    no_readings = MetragenReadings(water=(), gas=())
    with patch("custom_components.metragen.MetragenApiClient") as mock_class:
        instance = mock_class.return_value
        instance.async_login = AsyncMock(return_value=None)
        instance.async_get_readings = AsyncMock(
            side_effect=lambda year: (
                sample_readings if year == dt_util.now().year else no_readings
            )
        )
        yield instance


@pytest.fixture
async def setup_integration(
    recorder_mock, hass, mock_api_client, enable_custom_integrations
):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.metragen.const import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "user", "password": "pass"},
        unique_id="user",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
