"""Metragen resident portal client."""

from __future__ import annotations

import asyncio
import json
import re
import socket
from typing import TYPE_CHECKING, cast

import aiohttp

from .const import API_BASE_URL, LOGGER
from .data import (
    MetragenMeter,
    MetragenMeterKind,
    MetragenMeterReading,
    MetragenReadings,
)
from .exceptions import (
    MetragenApiClientAuthenticationError,
    MetragenApiClientCommunicationError,
    MetragenApiClientError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .data import MetragenReadingRow, MetragenReadResponse


_URL_QUERY_STRING = re.compile(r"\?\S*")
_LOGIN_FORM_MARKER = 'name="Senhaportal"'
_LITERS_PER_CUBIC_METER = 1000.0
_REQUEST_TIMEOUT_SECONDS = 30
_GRID_READ_FORM: Mapping[str, str] = {
    "sort": "",
    "page": "1",
    "pageSize": "1000",
    "group": "",
    "filter": "",
}


def _sanitized_error_text(exception: BaseException) -> str:
    """
    Strip URL query strings from upstream error text before it reaches the log.

    HTTP client libraries quote the request URL in their exception messages,
    and Home Assistant writes the message of an ``UpdateFailed`` to the log on
    every failed refresh. Redact the query string on the way out instead of
    trusting every future call site to remember.
    """
    return _URL_QUERY_STRING.sub("?<redacted>", str(exception))


def _cubic_meters(raw_liters: str | None) -> float:
    """Convert a raw counter value, reported in liters, to cubic meters."""
    return round(float(raw_liters or 0) / _LITERS_PER_CUBIC_METER, 3)


def _reading_from_row(row: MetragenReadingRow) -> MetragenMeterReading:
    """Build a reading from one grid row."""
    return MetragenMeterReading(
        year=row["Ano"],
        month=row["Mes"],
        previous_reading=_cubic_meters(row["Anterior"]),
        current_reading=_cubic_meters(row["Leitura"]),
        consumption=row["Consumodiv"] or 0.0,
        cost=row["Valordiv"] or 0.0,
    )


def _meters_from_rows(
    kind: MetragenMeterKind,
    rows: list[MetragenReadingRow],
) -> tuple[MetragenMeter, ...]:
    """Group grid rows by meter code, ordering each meter's readings by month."""
    readings_by_code: dict[str, list[MetragenMeterReading]] = {}
    for row in rows:
        readings_by_code.setdefault(row["Medidor"], []).append(_reading_from_row(row))
    return tuple(
        MetragenMeter(
            kind=kind,
            code=code,
            readings=tuple(
                sorted(readings, key=lambda reading: (reading.year, reading.month)),
            ),
        )
        for code, readings in sorted(readings_by_code.items())
    )


class MetragenApiClient:
    """
    Client for the Metragen resident portal.

    The portal is a cookie-authenticated ASP.NET MVC site, so the client must
    own a session with its own cookie jar and re-authenticate whenever the
    portal answers a grid request with an empty body — its way of saying the
    session lapsed. Residents sign in through ``Portal/AcessoAoPortal`` with
    the code or e-mail they registered; a rejected login redirects back to the
    login page instead of failing the request.
    """

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize."""
        self._username = username
        self._password = password
        self._session = session

    async def async_login(self) -> None:
        """Authenticate against the portal, raising when it rejects the credentials."""
        landing_page = await self._request_text(
            "post",
            f"{API_BASE_URL}/Portal/AcessoAoPortal",
            data={"Morador_id": self._username, "Senhaportal": self._password},
        )
        if _LOGIN_FORM_MARKER in landing_page:
            msg = "Failed to log in: the portal rejected the credentials"
            raise MetragenApiClientAuthenticationError(msg)
        LOGGER.debug("Logged in to the Metragen portal")

    async def async_get_readings(self, year: int) -> MetragenReadings:
        """Fetch the water and gas meters of one year, logging in when needed."""
        try:
            return await self._fetch_readings(year)
        except MetragenApiClientAuthenticationError:
            LOGGER.debug("Portal session missing or expired; logging in")
            await self.async_login()
            return await self._fetch_readings(year)

    async def _fetch_readings(self, year: int) -> MetragenReadings:
        """Select the year on the portal session and read both meter grids."""
        await self._request_text("post", f"{API_BASE_URL}/Portal/AreaMorador", data={})
        await self._request_text(
            "post",
            f"{API_BASE_URL}/Portal/FiltroAno",
            data={"ano": str(year)},
        )
        water_rows = await self._read_grid(
            f"{API_BASE_URL}/Portal/LeiturasMorador_Read"
        )
        gas_rows = await self._read_grid(
            f"{API_BASE_URL}/Portal/LeiturasMoradorGas_Read",
        )
        return MetragenReadings(
            water=_meters_from_rows(MetragenMeterKind.WATER, water_rows),
            gas=_meters_from_rows(MetragenMeterKind.GAS, gas_rows),
        )

    async def _read_grid(self, url: str) -> list[MetragenReadingRow]:
        """Read one Kendo grid, treating an empty body as a lapsed session."""
        text = await self._request_text("post", url, data=_GRID_READ_FORM)
        if not text.strip():
            msg = (
                "Failed to read the meter grid: the portal session is not authenticated"
            )
            raise MetragenApiClientAuthenticationError(msg)
        try:
            parsed = json.loads(text)
        except ValueError as exception:
            msg = f"Failed to parse the meter grid response: {exception}"
            raise MetragenApiClientError(msg) from exception
        if not isinstance(parsed, dict):
            msg = "Failed to parse the meter grid response: unexpected shape"
            raise MetragenApiClientError(msg)
        response = cast("MetragenReadResponse", parsed)
        return response["Data"] or []

    async def _request_text(
        self,
        method: str,
        url: str,
        data: Mapping[str, str] | None = None,
    ) -> str:
        """Perform an HTTP request and return the response body as text."""
        try:
            async with asyncio.timeout(_REQUEST_TIMEOUT_SECONDS):
                response = await self._session.request(
                    method=method,
                    url=url,
                    data=data,
                )
                response.raise_for_status()
                return await response.text()

        except TimeoutError as exception:
            detail = _sanitized_error_text(exception)
            msg = f"Timeout error fetching information - {detail}"
            raise MetragenApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            detail = _sanitized_error_text(exception)
            msg = f"Error fetching information - {detail}"
            raise MetragenApiClientCommunicationError(msg) from exception
        except MetragenApiClientError:
            raise
        except Exception as exception:
            msg = f"Failed to process the API response: {exception}"
            raise MetragenApiClientError(msg) from exception
