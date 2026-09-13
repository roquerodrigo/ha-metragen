"""Sensor platform for metragen."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback

from .monthly_consumption import MetragenMonthlyConsumptionSensor
from .monthly_cost import MetragenMonthlyCostSensor
from .reading import MetragenReadingSensor
from .yearly_consumption import MetragenYearlyConsumptionSensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ..coordinator import MetragenDataUpdateCoordinator
    from ..data import MetragenConfigEntry, MetragenMeter, MetragenPayload
    from ..entity import MetragenEntity


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: MetragenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform, adding meters as the portal starts listing them."""
    coordinator = entry.runtime_data.coordinator
    known_meter_keys: set[str] = set()

    @callback
    def _async_add_new_meters() -> None:
        payload: MetragenPayload | None = coordinator.data
        if payload is None:
            return
        new_meters = [
            meter for key, meter in payload.items() if key not in known_meter_keys
        ]
        if not new_meters:
            return
        known_meter_keys.update(meter.key for meter in new_meters)
        async_add_entities(
            [
                entity
                for meter in new_meters
                for entity in _entities_for_meter(coordinator, meter)
            ],
        )

    _async_add_new_meters()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_meters))


def _entities_for_meter(
    coordinator: MetragenDataUpdateCoordinator,
    meter: MetragenMeter,
) -> tuple[MetragenEntity, ...]:
    """Return the sensors every meter exposes."""
    return (
        MetragenReadingSensor(coordinator, meter),
        MetragenMonthlyConsumptionSensor(coordinator, meter),
        MetragenMonthlyCostSensor(coordinator, meter),
        MetragenYearlyConsumptionSensor(coordinator, meter),
    )
