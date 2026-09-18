"""Sensor que expõe o valor cobrado no período da leitura mais recente."""

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
    """Valor cobrado pelo medidor no último mês que o portal cobrou."""

    _attr_translation_key = "monthly_cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_BRAZILIAN_REAL
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2

    @property
    def unique_id(self) -> str:
        """Retorna um id único derivado da config entry e do medidor."""
        return (
            f"{self.coordinator.config_entry.entry_id}_{self._meter_key}_monthly_cost"
        )

    @property
    def native_value(self) -> float | None:
        """Retorna o valor da leitura mais recente."""
        latest = self.latest_reading
        return None if latest is None else latest.cost

    @property
    def last_reset(self) -> datetime | None:
        """Ancora o total no início do mês que a leitura cobre."""
        latest = self.latest_reading
        if latest is None:
            return None
        return dt_util.start_of_local_day(latest.period_start)
