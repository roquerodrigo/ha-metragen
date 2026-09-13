from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.metragen.const import DOMAIN
from custom_components.metragen.data import MetragenMeter, MetragenMeterKind
from custom_components.metragen.sensor.monthly_consumption import (
    MetragenMonthlyConsumptionSensor,
)
from custom_components.metragen.sensor.monthly_cost import MetragenMonthlyCostSensor
from custom_components.metragen.sensor.reading import MetragenReadingSensor
from custom_components.metragen.sensor.yearly_consumption import (
    MetragenYearlyConsumptionSensor,
)

from .conftest import COLD_WATER_METER, GAS_METER, make_reading

SENSORS_PER_METER = 4


def _coordinator(payload):
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "eid"
    coordinator.data = payload
    return coordinator


def _state_by_unique_id(hass, entry, suffix: str):
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_{suffix}"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    return state


async def test_every_meter_gets_its_sensors(hass, setup_integration, sample_payload):
    expected = len(sample_payload) * SENSORS_PER_METER
    assert len(hass.states.async_all("sensor")) == expected


async def test_reading_state_and_attributes(hass, setup_integration):
    state = _state_by_unique_id(hass, setup_integration, "water_af2616_reading")
    assert state.state == "86.72"
    assert state.attributes["unit_of_measurement"] == "m³"
    assert state.attributes["device_class"] == "water"
    assert state.attributes["state_class"] == "total_increasing"
    assert state.attributes["meter_code"] == "AF2616"
    assert state.attributes["year"] == 2026
    assert state.attributes["month"] == 7


async def test_gas_reading_uses_the_gas_device_class(hass, setup_integration):
    state = _state_by_unique_id(hass, setup_integration, "gas_aq2616_reading")
    assert state.state == "29.76"
    assert state.attributes["device_class"] == "gas"


async def test_monthly_cost_state(hass, setup_integration):
    state = _state_by_unique_id(hass, setup_integration, "water_af2616_monthly_cost")
    assert state.state == "101.576"
    assert state.attributes["unit_of_measurement"] == "BRL"
    assert state.attributes["device_class"] == "monetary"
    assert state.attributes["state_class"] == "total"
    assert (
        state.attributes["last_reset"]
        == dt_util.start_of_local_day(date(2026, 7, 1)).isoformat()
    )


async def test_devices_are_named_after_what_they_measure(hass, setup_integration):
    registry = dr.async_get(hass)
    entry_id = setup_integration.entry_id
    names = {
        key: registry.async_get_device(identifiers={(DOMAIN, f"{entry_id}_{key}")})
        for key in ("water_af2616", "water_aq2616", "gas_aq2616")
    }
    assert names["water_af2616"].name == "AF2616 Cold Water"
    assert names["water_aq2616"].name == "AQ2616 Hot Water"
    assert names["gas_aq2616"].name == "AQ2616 Gas"


async def test_meters_listed_later_are_added(hass, setup_integration, sample_payload):
    coordinator = setup_integration.runtime_data.coordinator
    new_meter = MetragenMeter(
        kind=MetragenMeterKind.WATER,
        code="AF9999",
        readings=(make_reading(2026, 7, 1.0, 1.0),),
    )
    coordinator.async_set_updated_data({**sample_payload, new_meter.key: new_meter})
    await hass.async_block_till_done()
    expected = (len(sample_payload) + 1) * SENSORS_PER_METER
    assert len(hass.states.async_all("sensor")) == expected
    state = _state_by_unique_id(hass, setup_integration, "water_af9999_reading")
    assert state.state == "1.0"


async def test_meters_dropped_by_the_portal_become_unavailable(
    hass, setup_integration, sample_payload
):
    coordinator = setup_integration.runtime_data.coordinator
    remaining = {k: v for k, v in sample_payload.items() if k != "water_af2616"}
    coordinator.async_set_updated_data(remaining)
    await hass.async_block_till_done()
    state = _state_by_unique_id(hass, setup_integration, "water_af2616_reading")
    assert state.state == "unavailable"


def test_reading_sensor_unique_id(sample_payload):
    sensor = MetragenReadingSensor(_coordinator(sample_payload), COLD_WATER_METER)
    assert sensor.unique_id == "eid_water_af2616_reading"


def test_reading_sensor_value_and_classes(sample_payload):
    sensor = MetragenReadingSensor(_coordinator(sample_payload), COLD_WATER_METER)
    assert sensor.native_value == 86.72
    assert sensor.device_class is SensorDeviceClass.WATER
    assert sensor.state_class is SensorStateClass.TOTAL_INCREASING


def test_reading_sensor_value_none_without_meter():
    sensor = MetragenReadingSensor(_coordinator({}), COLD_WATER_METER)
    assert sensor.native_value is None


def test_monthly_consumption_sensor(sample_payload):
    sensor = MetragenMonthlyConsumptionSensor(_coordinator(sample_payload), GAS_METER)
    assert sensor.unique_id == "eid_gas_aq2616_monthly_consumption"
    assert sensor.native_value == 3.89
    assert sensor.device_class is SensorDeviceClass.GAS
    assert sensor.state_class is SensorStateClass.TOTAL
    assert sensor.last_reset == dt_util.start_of_local_day(date(2026, 5, 1))


def test_monthly_consumption_sensor_without_meter():
    sensor = MetragenMonthlyConsumptionSensor(_coordinator({}), GAS_METER)
    assert sensor.native_value is None
    assert sensor.last_reset is None


def test_monthly_cost_sensor(sample_payload):
    sensor = MetragenMonthlyCostSensor(_coordinator(sample_payload), COLD_WATER_METER)
    assert sensor.unique_id == "eid_water_af2616_monthly_cost"
    assert sensor.native_value == 101.576
    assert sensor.device_class is SensorDeviceClass.MONETARY
    assert sensor.last_reset == dt_util.start_of_local_day(date(2026, 7, 1))


def test_monthly_cost_sensor_without_meter():
    sensor = MetragenMonthlyCostSensor(_coordinator({}), COLD_WATER_METER)
    assert sensor.native_value is None
    assert sensor.last_reset is None


def test_yearly_consumption_sensor(sample_payload):
    sensor = MetragenYearlyConsumptionSensor(
        _coordinator(sample_payload), COLD_WATER_METER
    )
    assert sensor.unique_id == "eid_water_af2616_yearly_consumption"
    assert sensor.native_value == 13.67
    assert sensor.device_class is SensorDeviceClass.WATER
    assert sensor.last_reset == dt_util.start_of_local_day(date(2026, 1, 1))


def test_yearly_consumption_sensor_without_meter():
    sensor = MetragenYearlyConsumptionSensor(_coordinator({}), COLD_WATER_METER)
    assert sensor.native_value is None
    assert sensor.last_reset is None
