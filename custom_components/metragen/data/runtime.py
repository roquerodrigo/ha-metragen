"""Runtime data stored on entry.runtime_data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.loader import Integration

    from ..api import MetragenApiClient
    from ..coordinator import MetragenDataUpdateCoordinator


@dataclass
class MetragenData:
    """Data stored on entry.runtime_data for the Metragen."""

    client: MetragenApiClient
    coordinator: MetragenDataUpdateCoordinator
    integration: Integration
