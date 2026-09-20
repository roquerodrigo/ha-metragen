from __future__ import annotations

import json
import socket
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.metragen.api import (
    MetragenApiClient,
    _sanitized_error_text,
)
from custom_components.metragen.const import API_BASE_URL
from custom_components.metragen.data import MetragenMeterKind
from custom_components.metragen.exceptions import (
    MetragenApiClientAuthenticationError,
    MetragenApiClientCommunicationError,
    MetragenApiClientError,
)

LOGIN_URL = f"{API_BASE_URL}/Portal/AcessoAoPortal"
LOGIN_PAGE = (
    '<form action="/metragen/Portal/AcessoAoPortal" method="post">'
    '<input id="Morador_id" name="Morador_id" type="text" value="" />'
    '<input id="Senhaportal" name="Senhaportal" type="password" />'
    "</form>"
)
LANDING_PAGE = "<legend>Morador: Someone - Apartamento: 1234 - Bloco: 0</legend>"


def _row(
    meter: str,
    month: int,
    counters: tuple[str | None, str | None],
    consumption: float | None,
    cost: float | None,
) -> dict:
    previous, current = counters
    return {
        "Ano": 2026,
        "Mes": month,
        "Medidor": meter,
        "Anterior": previous,
        "Leitura": current,
        "Anteriordiv": None if previous is None else float(previous) / 1000,
        "Consumodiv": consumption,
        "Valordiv": cost,
        "Morador_id": 99886,
        "Liberadomorador": True,
    }


WATER_GRID = json.dumps(
    {
        "Data": [
            _row("AQ1234", 7, ("33650", "39150"), 5.5, 0.0),
            _row("AF1234", 7, ("80250", "86350"), 6.1, 96.432),
            _row("AQ1234", 6, ("28450", "33650"), 5.2, 0.0),
            _row("AF1234", 6, ("72750", "80250"), 7.5, 120.456),
        ],
        "Total": 4,
        "AggregateResults": None,
        "Errors": None,
    }
)
GAS_GRID = json.dumps(
    {
        "Data": [_row("AQ1234", 5, ("24150", "28450"), 4.3, 140.98765)],
        "Total": 1,
        "AggregateResults": None,
        "Errors": None,
    }
)


def _response(body: str) -> MagicMock:
    response = MagicMock()
    response.status = 200
    response.raise_for_status = MagicMock()
    response.text = AsyncMock(return_value=body)
    return response


class FakePortal:
    """Roteia as requisições como o portal faz e acompanha o estado da sessão."""

    def __init__(
        self,
        *,
        logged_in: bool = False,
        accept_credentials: bool = True,
        water: str = WATER_GRID,
        gas: str = GAS_GRID,
    ) -> None:
        self.logged_in = logged_in
        self.accept_credentials = accept_credentials
        self.water = water
        self.gas = gas
        self.calls: list[tuple[str, str, dict | None]] = []

    async def request(self, method: str, url: str, data=None) -> MagicMock:
        self.calls.append((method, url, None if data is None else dict(data)))
        if url == LOGIN_URL:
            if self.accept_credentials:
                self.logged_in = True
                return _response(LANDING_PAGE)
            return _response(LOGIN_PAGE)
        if url.endswith("LeiturasMorador_Read"):
            return _response(self.water if self.logged_in else "")
        if url.endswith("LeiturasMoradorGas_Read"):
            return _response(self.gas if self.logged_in else "")
        return _response("")

    def calls_to(self, suffix: str) -> list[tuple[str, str, dict | None]]:
        return [call for call in self.calls if call[1].endswith(suffix)]


def _client(portal: FakePortal | None = None) -> MetragenApiClient:
    session = MagicMock()
    if portal is not None:
        session.request = AsyncMock(side_effect=portal.request)
    return MetragenApiClient(username="99886", password="p", session=session)


def _failing_client(side_effect: BaseException) -> MetragenApiClient:
    session = MagicMock()
    session.request = AsyncMock(side_effect=side_effect)
    return MetragenApiClient(username="u", password="p", session=session)


def test_communication_error_is_api_error():
    assert issubclass(MetragenApiClientCommunicationError, MetragenApiClientError)


def test_auth_error_is_api_error():
    assert issubclass(MetragenApiClientAuthenticationError, MetragenApiClientError)


def test_api_error_is_exception():
    assert issubclass(MetragenApiClientError, Exception)


async def test_login_posts_the_resident_credentials():
    portal = FakePortal()
    await _client(portal).async_login()
    assert portal.calls == [
        ("post", LOGIN_URL, {"Morador_id": "99886", "Senhaportal": "p"}),
    ]


async def test_login_rejected_raises_auth_error():
    portal = FakePortal(accept_credentials=False)
    with pytest.raises(MetragenApiClientAuthenticationError, match="rejected"):
        await _client(portal).async_login()


async def test_get_readings_groups_rows_by_meter_in_chronological_order():
    readings = await _client(FakePortal(logged_in=True)).async_get_readings(2026)
    assert [meter.code for meter in readings.water] == ["AF1234", "AQ1234"]
    assert [meter.code for meter in readings.gas] == ["AQ1234"]
    cold_water = readings.water[0]
    assert cold_water.kind is MetragenMeterKind.WATER
    assert [reading.month for reading in cold_water.readings] == [6, 7]
    assert readings.gas[0].kind is MetragenMeterKind.GAS


async def test_get_readings_converts_counters_from_liters_to_cubic_meters():
    readings = await _client(FakePortal(logged_in=True)).async_get_readings(2026)
    latest = readings.water[0].latest
    assert latest is not None
    assert latest.previous_reading == 80.25
    assert latest.current_reading == 86.35
    assert latest.consumption == 6.1
    assert latest.cost == 96.432


async def test_get_readings_selects_the_requested_year():
    portal = FakePortal(logged_in=True)
    await _client(portal).async_get_readings(2025)
    assert portal.calls_to("/Portal/FiltroAno")[0][2] == {"ano": "2025"}


async def test_get_readings_opens_the_resident_area_first():
    portal = FakePortal(logged_in=True)
    await _client(portal).async_get_readings(2026)
    assert portal.calls[0][1] == f"{API_BASE_URL}/Portal/AreaMorador"


async def test_get_readings_sends_the_grid_read_form():
    portal = FakePortal(logged_in=True)
    await _client(portal).async_get_readings(2026)
    form = portal.calls_to("LeiturasMorador_Read")[0][2]
    assert form is not None
    assert form["page"] == "1"
    assert "pageSize" in form


async def test_get_readings_logs_in_when_the_session_lapsed():
    portal = FakePortal(logged_in=False)
    readings = await _client(portal).async_get_readings(2026)
    assert len(readings.water) == 2
    assert len(portal.calls_to("LeiturasMorador_Read")) == 2
    assert len(portal.calls_to("/Portal/AcessoAoPortal")) == 1


async def test_get_readings_does_not_log_in_while_the_session_is_valid():
    portal = FakePortal(logged_in=True)
    await _client(portal).async_get_readings(2026)
    assert portal.calls_to("/Portal/AcessoAoPortal") == []


async def test_get_readings_raises_auth_error_when_login_does_not_help():
    portal = FakePortal(logged_in=True, water="", gas="")
    with pytest.raises(MetragenApiClientAuthenticationError, match="not authenticated"):
        await _client(portal).async_get_readings(2026)


async def test_get_readings_propagates_rejected_credentials():
    portal = FakePortal(logged_in=False, accept_credentials=False)
    with pytest.raises(MetragenApiClientAuthenticationError, match="rejected"):
        await _client(portal).async_get_readings(2026)


async def test_get_readings_treats_null_data_as_no_meters():
    portal = FakePortal(logged_in=True, gas=json.dumps({"Data": None, "Total": 0}))
    readings = await _client(portal).async_get_readings(2026)
    assert readings.gas == ()


async def test_get_readings_rejects_invalid_json():
    portal = FakePortal(logged_in=True, water="<html>oops</html>")
    with pytest.raises(MetragenApiClientError, match="parse"):
        await _client(portal).async_get_readings(2026)


async def test_get_readings_rejects_a_non_object_response():
    portal = FakePortal(logged_in=True, water="[]")
    with pytest.raises(MetragenApiClientError, match="unexpected shape"):
        await _client(portal).async_get_readings(2026)


async def test_get_readings_defaults_missing_values_to_zero():
    grid = json.dumps({"Data": [_row("AF1234", 3, (None, None), None, None)]})
    portal = FakePortal(logged_in=True, water=grid)
    readings = await _client(portal).async_get_readings(2026)
    latest = readings.water[0].latest
    assert latest is not None
    assert latest.previous_reading == 0.0
    assert latest.current_reading == 0.0
    assert latest.consumption == 0.0
    assert latest.cost == 0.0


async def test_request_timeout_raises_communication_error():
    client = _failing_client(TimeoutError("timed out"))
    with pytest.raises(MetragenApiClientCommunicationError, match="Timeout"):
        await client._request_text("get", "http://x")


async def test_request_client_error_raises_communication_error():
    client = _failing_client(aiohttp.ClientError("refused"))
    with pytest.raises(MetragenApiClientCommunicationError, match="Error fetching"):
        await client._request_text("get", "http://x")


async def test_request_socket_error_raises_communication_error():
    client = _failing_client(socket.gaierror("dns"))
    with pytest.raises(MetragenApiClientCommunicationError, match="Error fetching"):
        await client._request_text("get", "http://x")


async def test_request_unexpected_exception_raises_api_error():
    client = _failing_client(RuntimeError("boom"))
    with pytest.raises(MetragenApiClientError, match="Failed to process"):
        await client._request_text("get", "http://x")


async def test_request_http_error_raises_communication_error():
    response = _response("")
    response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        request_info=MagicMock(), history=()
    )
    session = MagicMock()
    session.request = AsyncMock(return_value=response)
    client = MetragenApiClient(username="u", password="p", session=session)
    with pytest.raises(MetragenApiClientCommunicationError):
        await client._request_text("get", "http://x")


def test_sanitized_error_text_redacts_the_query_string():
    exception = aiohttp.ClientError(
        "Cannot connect to https://example.com/posts?api_key=supersecret"
    )
    sanitized = _sanitized_error_text(exception)
    assert "supersecret" not in sanitized
    assert sanitized.endswith("https://example.com/posts?<redacted>")


def test_sanitized_error_text_keeps_text_without_a_query_string():
    assert _sanitized_error_text(TimeoutError("timed out")) == "timed out"


async def test_request_client_error_message_hides_credentials():
    client = _failing_client(
        aiohttp.ClientError("GET https://example.com/posts?token=hunter2")
    )
    with pytest.raises(MetragenApiClientCommunicationError) as excinfo:
        await client._request_text("get", "http://x")
    assert "hunter2" not in str(excinfo.value)
    assert "<redacted>" in str(excinfo.value)
