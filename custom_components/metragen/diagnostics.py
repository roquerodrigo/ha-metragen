"""Diagnostics support for metragen."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, cast

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.core import HomeAssistant

    from .data import (
        JsonObject,
        MetragenConfigEntry,
        MetragenDiagnosticsEntry,
        MetragenDiagnosticsPayload,
        MetragenPayload,
    )

TO_REDACT: frozenset[str] = frozenset({CONF_PASSWORD, CONF_USERNAME})


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: MetragenConfigEntry,
) -> MetragenDiagnosticsPayload:
    """Return diagnostics for a config entry."""
    redacted_data = cast(
        "Mapping[str, str]",
        async_redact_data(dict(entry.data), set(TO_REDACT)),
    )
    redacted_options = cast(
        "Mapping[str, str | int]",
        async_redact_data(dict(entry.options), set(TO_REDACT)),
    )
    diag_entry: MetragenDiagnosticsEntry = {
        "title": entry.title,
        "version": entry.version,
        "domain": entry.domain,
        "data": redacted_data,
        "options": redacted_options,
    }
    payload: MetragenPayload | None = entry.runtime_data.coordinator.data
    coordinator_data: Mapping[str, JsonObject] | None = (
        None
        if payload is None
        else {key: cast("JsonObject", asdict(meter)) for key, meter in payload.items()}
    )
    return {
        "entry": diag_entry,
        "coordinator_data": coordinator_data,
    }
