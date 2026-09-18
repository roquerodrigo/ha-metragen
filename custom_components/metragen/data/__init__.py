"""Tipos próprios do metragen."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from .config_data import MetragenConfigData
from .diagnostics_entry import MetragenDiagnosticsEntry
from .diagnostics_payload import MetragenDiagnosticsPayload
from .meter import MetragenMeter
from .meter_kind import MetragenMeterKind
from .meter_reading import MetragenMeterReading
from .options_data import MetragenOptionsData
from .read_response import MetragenReadResponse
from .reading_row import MetragenReadingRow
from .readings import MetragenReadings
from .runtime import MetragenData

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | Mapping[str, JsonValue]
type JsonObject = Mapping[str, JsonValue]

type MetragenPayload = Mapping[str, MetragenMeter]
type MetragenConfigEntry = ConfigEntry[MetragenData]

__all__ = [
    "JsonObject",
    "JsonPrimitive",
    "JsonValue",
    "MetragenConfigData",
    "MetragenConfigEntry",
    "MetragenData",
    "MetragenDiagnosticsEntry",
    "MetragenDiagnosticsPayload",
    "MetragenMeter",
    "MetragenMeterKind",
    "MetragenMeterReading",
    "MetragenOptionsData",
    "MetragenPayload",
    "MetragenReadResponse",
    "MetragenReadingRow",
    "MetragenReadings",
]
