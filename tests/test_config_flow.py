from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.metragen.const import DOMAIN
from custom_components.metragen.exceptions import (
    MetragenApiClientAuthenticationError,
    MetragenApiClientCommunicationError,
    MetragenApiClientError,
)

USER_INPUT = {"username": "user", "password": "pass"}
NEW_INPUT = {"username": "user", "password": "newpass"}


@pytest.fixture(autouse=True)
def _recorder(recorder_mock):
    """Every flow loads the integration, whose dependencies include the recorder."""


def _patch_client():
    return patch("custom_components.metragen.config_flow.MetragenApiClient")


async def _start_user_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_step_user_shows_form(hass, enable_custom_integrations):
    result = await _start_user_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_step_user_success_creates_entry(hass, enable_custom_integrations):
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(return_value=None)
        result = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=USER_INPUT
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "user"
    assert result["data"] == USER_INPUT


async def test_step_user_success_sets_unique_id(hass, enable_custom_integrations):
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(return_value=None)
        flow = await _start_user_flow(hass)
        await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input=USER_INPUT
        )
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.unique_id == "user"


async def test_step_user_duplicate_aborts(hass, enable_custom_integrations):
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(return_value=None)
        flow1 = await _start_user_flow(hass)
        await hass.config_entries.flow.async_configure(
            flow1["flow_id"], user_input=USER_INPUT
        )
        flow2 = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            flow2["flow_id"], user_input=USER_INPUT
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_step_user_auth_error_shows_auth(hass, enable_custom_integrations):
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(
            side_effect=MetragenApiClientAuthenticationError("bad")
        )
        flow = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input=USER_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "auth"


async def test_step_user_communication_error_shows_connection(
    hass, enable_custom_integrations
):
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(
            side_effect=MetragenApiClientCommunicationError("down")
        )
        flow = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input=USER_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "connection"


async def test_step_user_generic_error_shows_unknown(hass, enable_custom_integrations):
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(
            side_effect=MetragenApiClientError("oops")
        )
        flow = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input=USER_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"


# --- Reauth ----------------------------------------------------------------


def _existing_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, unique_id="user")
    entry.add_to_hass(hass)
    return entry


async def test_reauth_shows_confirm_form(hass, enable_custom_integrations):
    entry = _existing_entry(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


async def test_reauth_success_updates_entry(hass, enable_custom_integrations):
    entry = _existing_entry(hass)
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(return_value=None)
        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=NEW_INPUT
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "newpass"


async def test_reauth_different_account_aborts(hass, enable_custom_integrations):
    entry = _existing_entry(hass)
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(return_value=None)
        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"username": "another_user", "password": "newpass"},
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    assert entry.data["username"] == "user"
    assert entry.data["password"] == "pass"


async def test_reauth_auth_error_shows_auth(hass, enable_custom_integrations):
    entry = _existing_entry(hass)
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(
            side_effect=MetragenApiClientAuthenticationError("nope")
        )
        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=NEW_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "auth"


# --- Reconfigure -----------------------------------------------------------


async def test_reconfigure_shows_form(hass, enable_custom_integrations):
    entry = _existing_entry(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"


async def test_reconfigure_success_updates_entry(hass, enable_custom_integrations):
    entry = _existing_entry(hass)
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(return_value=None)
        result = await entry.start_reconfigure_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=NEW_INPUT
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["password"] == "newpass"


async def test_reconfigure_different_account_aborts(hass, enable_custom_integrations):
    entry = _existing_entry(hass)
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(return_value=None)
        result = await entry.start_reconfigure_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"username": "another_user", "password": "newpass"},
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    assert entry.data["username"] == "user"
    assert entry.data["password"] == "pass"


async def test_reconfigure_communication_error_shows_connection(
    hass, enable_custom_integrations
):
    entry = _existing_entry(hass)
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(
            side_effect=MetragenApiClientCommunicationError("down")
        )
        result = await entry.start_reconfigure_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=NEW_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "connection"


async def test_reconfigure_generic_error_shows_unknown(
    hass, enable_custom_integrations
):
    entry = _existing_entry(hass)
    with _patch_client() as mock:
        mock.return_value.async_login = AsyncMock(
            side_effect=MetragenApiClientError("oops")
        )
        result = await entry.start_reconfigure_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=NEW_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"
