from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorDeviceClass

from custom_components.metragen.const import ATTRIBUTION, DOMAIN
from custom_components.metragen.entity import MetragenEntity

from .conftest import COLD_WATER_METER, GAS_METER


def _make_entity(
    meter=COLD_WATER_METER, payload=None, entry_id="eid", *, update_success=True
) -> MetragenEntity:
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = entry_id
    coordinator.data = payload
    coordinator.last_update_success = update_success
    return MetragenEntity(coordinator=coordinator, meter=meter)


def test_attribution():
    assert _make_entity()._attr_attribution == ATTRIBUTION


def test_has_entity_name():
    assert _make_entity()._attr_has_entity_name is True


def test_device_info_identifiers_combine_entry_id_and_meter_key():
    identifiers = _make_entity(entry_id="my_id").device_info["identifiers"]
    assert identifiers == {(DOMAIN, "my_id_water_af1234")}


def test_device_info_manufacturer():
    assert _make_entity().device_info["manufacturer"] == "Metragen"


def test_device_info_translates_the_meter_kind_with_its_code():
    info = _make_entity().device_info
    assert info["translation_key"] == "cold_water_meter"
    assert info["translation_placeholders"] == {"code": "AF1234"}


def test_meter_is_none_before_first_refresh():
    assert _make_entity(payload=None).meter is None


def test_meter_is_none_once_the_portal_drops_it():
    assert _make_entity(payload={}).meter is None


def test_meter_resolves_from_the_payload(sample_payload):
    assert _make_entity(payload=sample_payload).meter is COLD_WATER_METER


def test_latest_reading_comes_from_the_meter(sample_payload):
    entity = _make_entity(payload=sample_payload)
    assert entity.latest_reading == COLD_WATER_METER.readings[-1]


def test_latest_reading_is_none_without_meter():
    assert _make_entity(payload={}).latest_reading is None


def test_meter_device_class_water():
    assert _make_entity().meter_device_class is SensorDeviceClass.WATER


def test_meter_device_class_gas():
    assert _make_entity(meter=GAS_METER).meter_device_class is SensorDeviceClass.GAS


def test_available_when_meter_listed(sample_payload):
    assert _make_entity(payload=sample_payload).available is True


def test_unavailable_when_meter_dropped():
    assert _make_entity(payload={}).available is False


def test_unavailable_when_last_update_failed(sample_payload):
    entity = _make_entity(payload=sample_payload, update_success=False)
    assert entity.available is False


def test_extra_state_attributes_describe_the_billing_month(sample_payload):
    assert _make_entity(payload=sample_payload).extra_state_attributes == {
        "meter_code": "AF1234",
        "year": 2026,
        "month": 7,
    }


def test_extra_state_attributes_empty_without_reading():
    assert _make_entity(payload={}).extra_state_attributes == {}


def test_coordinator_stored():
    coord = MagicMock()
    coord.config_entry.entry_id = "eid"
    entity = MetragenEntity(coordinator=coord, meter=COLD_WATER_METER)
    assert entity.coordinator is coord
