"""Sensor exposing the amount billed for the latest reading period."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.util import dt as dt_util

from ..const import CURRENCY_BRAZILIAN_REAL
from ..entity import MetragenEntity

if TYPE_CHECKING:
    from datetime import datetime


class MetragenMonthlyCostSensor(MetragenEntity, SensorEntity):
    """Amount charged for the meter in the latest month the portal has billed."""

    _attr_translation_key = "monthly_cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_BRAZILIAN_REAL
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2

    @property
    def unique_id(self) -> str:
        """Return a unique id derived from the config entry and the meter."""
        return (
            f"{self.coordinator.config_entry.entry_id}_{self._meter_key}_monthly_cost"
        )

    @property
    def native_value(self) -> float | None:
        """Return the cost of the latest reading."""
        latest = self.latest_reading
        return None if latest is None else latest.cost

    @property
    def last_reset(self) -> datetime | None:
        """Anchor the total at the start of the month the reading covers."""
        latest = self.latest_reading
        if latest is None:
            return None
        return dt_util.start_of_local_day(latest.period_start)
