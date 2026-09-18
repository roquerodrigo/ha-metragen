"""Cliente do portal do morador Metragen."""

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
    Remove a query string das URLs no texto de erro antes que ele chegue ao log.

    Bibliotecas de cliente HTTP citam a URL da requisição nas mensagens de
    exceção, e o Home Assistant grava no log a mensagem de um ``UpdateFailed``
    a cada atualização que falha. A query string é ocultada na saída, em vez de
    confiar que todo ponto de chamada futuro se lembre disso.
    """
    return _URL_QUERY_STRING.sub("?<redacted>", str(exception))


def _cubic_meters(raw_liters: str | None) -> float:
    """Transforma o valor bruto do contador, informado em litros, em metros cúbicos."""
    return round(float(raw_liters or 0) / _LITERS_PER_CUBIC_METER, 3)


def _reading_from_row(row: MetragenReadingRow) -> MetragenMeterReading:
    """Monta uma leitura a partir de uma linha do grid."""
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
    """Agrupa as linhas do grid por código de medidor, ordenando as leituras por mês."""
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
    Cliente do portal do morador Metragen.

    O portal é um site ASP.NET MVC autenticado por cookie, então o cliente
    precisa ter uma sessão com cookie jar próprio e se reautenticar sempre que
    o portal responder a uma requisição de grid com corpo vazio — a forma dele
    de dizer que a sessão expirou. O morador entra por
    ``Portal/AcessoAoPortal`` com o código ou e-mail cadastrado; um login
    rejeitado redireciona de volta à página de login em vez de falhar a
    requisição.
    """

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Inicializa."""
        self._username = username
        self._password = password
        self._session = session

    async def async_login(self) -> None:
        """Autentica no portal, levantando erro quando ele rejeita as credenciais."""
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
        """Busca os medidores de água e gás de um ano, fazendo login quando preciso."""
        try:
            return await self._fetch_readings(year)
        except MetragenApiClientAuthenticationError:
            LOGGER.debug("Portal session missing or expired; logging in")
            await self.async_login()
            return await self._fetch_readings(year)

    async def _fetch_readings(self, year: int) -> MetragenReadings:
        """Seleciona o ano na sessão do portal e lê os dois grids de medidores."""
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
        """Lê um grid Kendo, tratando corpo vazio como sessão expirada."""
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
        """Faz uma requisição HTTP e retorna o corpo da resposta como texto."""
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
