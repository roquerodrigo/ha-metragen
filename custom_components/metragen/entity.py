"""MetragenEntity base class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import MetragenDataUpdateCoordinator
from .data import MetragenMeterKind

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .data import MetragenMeter, MetragenMeterReading, MetragenPayload

_DEVICE_CLASS_BY_KIND: Mapping[MetragenMeterKind, SensorDeviceClass] = {
    MetragenMeterKind.WATER: SensorDeviceClass.WATER,
    MetragenMeterKind.GAS: SensorDeviceClass.GAS,
}


class MetragenEntity(CoordinatorEntity[MetragenDataUpdateCoordinator]):
    """Base entity bound to one meter of the resident account."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MetragenDataUpdateCoordinator,
        meter: MetragenMeter,
    ) -> None:
        """Bind the entity to the meter it reports."""
        super().__init__(coordinator)
        self._meter_key = meter.key
        self._meter_identity = meter

    @property
    def meter(self) -> MetragenMeter | None:
        """Return the meter as last fetched, or None once the portal drops it."""
        payload: MetragenPayload | None = self.coordinator.data
        if payload is None:
            return None
        return payload.get(self._meter_key)

    @property
    def latest_reading(self) -> MetragenMeterReading | None:
        """Return the most recent reading of the meter, if any."""
        meter = self.meter
        return None if meter is None else meter.latest

    @property
    def meter_device_class(self) -> SensorDeviceClass:
        """Return the sensor device class matching the utility the meter measures."""
        return _DEVICE_CLASS_BY_KIND[self._meter_identity.kind]

    @property
    def available(self) -> bool:
        """Report unavailable once the portal stops listing the meter."""
        return super().available and self.latest_reading is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return one device per meter, named after what it measures."""
        meter = self._meter_identity
        return DeviceInfo(
            identifiers={
                (DOMAIN, f"{self.coordinator.config_entry.entry_id}_{meter.key}"),
            },
            manufacturer="Metragen",
            translation_key=meter.device_translation_key,
            translation_placeholders={"code": meter.code},
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, str | int]:
        """Expose which meter and billing month the state refers to."""
        latest = self.latest_reading
        if latest is None:
            return {}
        return {
            "meter_code": self._meter_identity.code,
            "year": latest.year,
            "month": latest.month,
        }
