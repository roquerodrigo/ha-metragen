"""Formato tipado de topo retornado por async_get_config_entry_diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping

    from . import JsonObject
    from .diagnostics_entry import MetragenDiagnosticsEntry


class MetragenDiagnosticsPayload(TypedDict):
    """Formato de topo retornado por async_get_config_entry_diagnostics."""

    entry: MetragenDiagnosticsEntry
    coordinator_data: Mapping[str, JsonObject] | None
