"""Suporte a diagnóstico do metragen."""

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

# O título da entrada é o login, e o código do medidor identifica a unidade.
TO_REDACT: frozenset[str] = frozenset({CONF_PASSWORD, CONF_USERNAME, "title", "code"})


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: MetragenConfigEntry,
) -> MetragenDiagnosticsPayload:
    """Retorna o diagnóstico de uma config entry."""
    diag_entry = cast(
        "MetragenDiagnosticsEntry",
        async_redact_data(
            {
                "title": entry.title,
                "version": entry.version,
                "domain": entry.domain,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            set(TO_REDACT),
        ),
    )
    payload: MetragenPayload | None = entry.runtime_data.coordinator.data
    coordinator_data: Mapping[str, JsonObject] | None = (
        None
        if payload is None
        else {
            f"meter_{index}": cast(
                "JsonObject", async_redact_data(asdict(meter), set(TO_REDACT))
            )
            for index, meter in enumerate(payload.values(), start=1)
        }
    )
    return {
        "entry": diag_entry,
        "coordinator_data": coordinator_data,
    }
