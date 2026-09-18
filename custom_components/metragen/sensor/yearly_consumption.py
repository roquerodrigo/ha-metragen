"""Sensor que expõe o consumo acumulado ao longo do ano corrente."""

from __future__ import annotations

from datetime import date
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


class MetragenYearlyConsumptionSensor(MetragenEntity, SensorEntity):
    """Volume consumido desde o início do ano da leitura mais recente."""

    _attr_translation_key = "yearly_consumption"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 3

    @property
    def unique_id(self) -> str:
        """Retorna um id único derivado da config entry e do medidor."""
        entry_id = self.coordinator.config_entry.entry_id
        return f"{entry_id}_{self._meter_key}_yearly_consumption"

    @property
    def device_class(self) -> SensorDeviceClass:
        """Acompanha o insumo que o medidor mede."""
        return self.meter_device_class

    @property
    def native_value(self) -> float | None:
        """Retorna o consumo acumulado no ano da leitura mais recente."""
        meter = self.meter
        if meter is None or meter.latest is None:
            return None
        return meter.yearly_consumption

    @property
    def last_reset(self) -> datetime | None:
        """Ancora o total no primeiro dia do ano a que a leitura pertence."""
        latest = self.latest_reading
        if latest is None:
            return None
        return dt_util.start_of_local_day(date(latest.year, 1, 1))
