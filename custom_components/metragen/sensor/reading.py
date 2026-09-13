"""Sensor exposing the latest counter value of a meter."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume

from ..entity import MetragenEntity


class MetragenReadingSensor(MetragenEntity, SensorEntity):
    """Latest counter value of the meter, suitable as an energy dashboard source."""

    _attr_translation_key = "reading"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3

    @property
    def unique_id(self) -> str:
        """Return a unique id derived from the config entry and the meter."""
        return f"{self.coordinator.config_entry.entry_id}_{self._meter_key}_reading"

    @property
    def device_class(self) -> SensorDeviceClass:
        """Match the utility the meter measures."""
        return self.meter_device_class

    @property
    def native_value(self) -> float | None:
        """Return the counter value of the latest reading."""
        latest = self.latest_reading
        return None if latest is None else latest.current_reading
