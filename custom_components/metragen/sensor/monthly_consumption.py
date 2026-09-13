"""Sensor exposing the consumption billed in the latest reading period."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume
from homeassistant.util import dt as dt_util

from ..entity import MetragenEntity

if TYPE_CHECKING:
    from datetime import datetime


class MetragenMonthlyConsumptionSensor(MetragenEntity, SensorEntity):
    """Volume consumed in the latest month the portal has billed."""

    _attr_translation_key = "monthly_consumption"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 3

    @property
    def unique_id(self) -> str:
        """Return a unique id derived from the config entry and the meter."""
        entry_id = self.coordinator.config_entry.entry_id
        return f"{entry_id}_{self._meter_key}_monthly_consumption"

    @property
    def device_class(self) -> SensorDeviceClass:
        """Match the utility the meter measures."""
        return self.meter_device_class

    @property
    def native_value(self) -> float | None:
        """Return the consumption of the latest reading."""
        latest = self.latest_reading
        return None if latest is None else latest.consumption

    @property
    def last_reset(self) -> datetime | None:
        """Anchor the total at the start of the month the reading covers."""
        latest = self.latest_reading
        if latest is None:
            return None
        return dt_util.start_of_local_day(latest.period_start)
