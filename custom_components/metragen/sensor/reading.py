"""Sensor que expõe o valor mais recente do contador de um medidor."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume

from ..entity import MetragenEntity


class MetragenReadingSensor(MetragenEntity, SensorEntity):
    """Valor mais recente do contador, adequado como fonte do painel de energia."""

    _attr_translation_key = "reading"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3

    @property
    def unique_id(self) -> str:
        """Retorna um id único derivado da config entry e do medidor."""
        return f"{self.coordinator.config_entry.entry_id}_{self._meter_key}_reading"

    @property
    def device_class(self) -> SensorDeviceClass:
        """Acompanha o insumo que o medidor mede."""
        return self.meter_device_class

    @property
    def native_value(self) -> float | None:
        """Retorna o valor do contador na leitura mais recente."""
        latest = self.latest_reading
        return None if latest is None else latest.current_reading
