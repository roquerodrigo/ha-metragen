"""Constants for metragen."""

from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "metragen"
ATTRIBUTION = "Data provided by Sistema Metragen"
API_BASE_URL = "https://www.sistemametragen.com.br/metragen"
CURRENCY_BRAZILIAN_REAL = "BRL"

DEFAULT_SCAN_INTERVAL_SECONDS = 3600
MIN_SCAN_INTERVAL_SECONDS = 300
