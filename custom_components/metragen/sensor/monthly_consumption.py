"""Sensor que expõe o consumo cobrado no período da leitura mais recente."""

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
    """Volume consumido no último mês que o portal cobrou."""

    _attr_translation_key = "monthly_consumption"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 3

    @property
    def unique_id(self) -> str:
        """Retorna um id único derivado da config entry e do medidor."""
        entry_id = self.coordinator.config_entry.entry_id
        return f"{entry_id}_{self._meter_key}_monthly_consumption"

    @property
    def device_class(self) -> SensorDeviceClass:
        """Acompanha o insumo que o medidor mede."""
        return self.meter_device_class

    @property
    def native_value(self) -> float | None:
        """Retorna o consumo da leitura mais recente."""
        latest = self.latest_reading
        return None if latest is None else latest.consumption

    @property
    def last_reset(self) -> datetime | None:
        """Ancora o total no início do mês que a leitura cobre."""
        latest = self.latest_reading
        if latest is None:
            return None
        return dt_util.start_of_local_day(latest.period_start)
