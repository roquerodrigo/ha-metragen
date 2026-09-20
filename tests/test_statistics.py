from __future__ import annotations

import logging
from datetime import date
from functools import partial
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    get_metadata,
    statistics_during_period,
)
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.metragen.data import (
    MetragenMeter,
    MetragenMeterKind,
    MetragenReadings,
)
from custom_components.metragen.exceptions import (
    MetragenApiClientCommunicationError,
)
from custom_components.metragen.statistics import (
    MAX_HISTORY_YEARS,
    MetragenStatisticsImporter,
)

from .conftest import COLD_WATER_METER, GAS_METER, make_reading

EMPTY = MetragenReadings(water=(), gas=())
CURRENT_YEAR = 2026
CONSUMPTION_ID = "metragen:af1234_water"
COST_ID = "metragen:af1234_water_cost"
TRANSLATIONS = {
    "component.metragen.device.cold_water_meter.name": "{code} Cold Water",
    "component.metragen.device.hot_water_meter.name": "{code} Hot Water",
    "component.metragen.device.gas_meter.name": "{code} Gas",
    "component.metragen.entity.sensor.monthly_cost.name": "Monthly Cost",
}


def _month_start(year: int, month: int):
    return dt_util.start_of_local_day(date(year, month, 1))


def _last_row(statistic_id: str, year: int, month: int, total: float) -> dict:
    return {
        statistic_id: [{"start": _month_start(year, month).timestamp(), "sum": total}]
    }


@pytest.fixture
def recorder():
    with (
        patch("custom_components.metragen.statistics.get_instance") as get_instance,
        patch(
            "custom_components.metragen.statistics.get_last_statistics",
            return_value={},
        ) as last_statistics,
        patch(
            "custom_components.metragen.statistics.async_add_external_statistics"
        ) as add_statistics,
        patch(
            "custom_components.metragen.statistics.async_get_cached_translations",
            return_value=TRANSLATIONS,
        ),
    ):
        get_instance.return_value.async_add_executor_job = AsyncMock(
            side_effect=lambda func, *args: func(*args)
        )
        yield SimpleNamespace(last=last_statistics, add=add_statistics)


def _client(readings_by_year: dict[int, MetragenReadings]) -> MagicMock:
    client = MagicMock()
    client.async_get_readings = AsyncMock(
        side_effect=lambda year: readings_by_year.get(year, EMPTY)
    )
    return client


def _importer(client: MagicMock) -> MetragenStatisticsImporter:
    return MetragenStatisticsImporter(
        hass=MagicMock(),
        client=client,
        current_year=CURRENT_YEAR,
    )


def _import_call(recorder, statistic_id: str):
    for call in recorder.add.call_args_list:
        if call.args[1]["statistic_id"] == statistic_id:
            return call
    pytest.fail(f"{statistic_id} was not imported")


def _rows(recorder, statistic_id: str) -> list[dict]:
    return _import_call(recorder, statistic_id).args[2]


def _metadata(recorder, statistic_id: str) -> dict:
    return _import_call(recorder, statistic_id).args[1]


async def test_first_import_walks_back_until_an_empty_year(recorder):
    older = MetragenMeter(
        kind=MetragenMeterKind.WATER,
        code="AF1234",
        readings=(
            make_reading(2025, 11, 60.0, 4.0, 40.0),
            make_reading(2025, 12, 65.0, 5.0, 50.0),
        ),
    )
    client = _client({2025: MetragenReadings(water=(older,), gas=())})
    await _importer(client).async_import([COLD_WATER_METER])
    assert [call.args[0] for call in client.async_get_readings.await_args_list] == [
        2025,
        2024,
    ]
    rows = _rows(recorder, CONSUMPTION_ID)
    assert [row["start"] for row in rows] == [
        _month_start(2025, 11),
        _month_start(2025, 12),
        _month_start(2026, 6),
        _month_start(2026, 7),
    ]
    assert [row["sum"] for row in rows] == [4.0, 9.0, 16.5, 22.6]
    assert [row["state"] for row in rows] == [60.0, 65.0, 80.25, 86.35]


async def test_first_import_writes_the_cost_series(recorder):
    await _importer(_client({})).async_import([COLD_WATER_METER])
    rows = _rows(recorder, COST_ID)
    assert [row["state"] for row in rows] == [120.456, 96.432]
    assert [row["sum"] for row in rows] == [120.46, 216.89]


async def test_metadata_describes_volume_and_currency(recorder):
    await _importer(_client({})).async_import([COLD_WATER_METER])
    consumption = _metadata(recorder, CONSUMPTION_ID)
    assert consumption["source"] == "metragen"
    assert consumption["has_sum"] is True
    assert consumption["unit_of_measurement"] == "m³"
    assert consumption["unit_class"] == "volume"
    assert consumption["name"] == "AF1234 Cold Water"
    cost = _metadata(recorder, COST_ID)
    assert cost["name"] == "AF1234 Cold Water Monthly Cost"
    assert cost["unit_of_measurement"] == "BRL"
    assert cost["unit_class"] is None


async def test_gas_meter_uses_its_own_statistic_ids(recorder):
    await _importer(_client({})).async_import([GAS_METER])
    assert _rows(recorder, "metragen:aq1234_gas")
    assert _rows(recorder, "metragen:aq1234_gas_cost")
    assert _metadata(recorder, "metragen:aq1234_gas")["name"] == "AQ1234 Gas"


async def test_first_import_stops_after_the_history_cap(recorder):
    always_data = {
        year: MetragenReadings(water=(COLD_WATER_METER,), gas=())
        for year in range(CURRENT_YEAR - 30, CURRENT_YEAR)
    }
    client = _client(always_data)
    await _importer(client).async_import([COLD_WATER_METER])
    assert client.async_get_readings.await_count == MAX_HISTORY_YEARS


async def test_first_import_merges_months_fetched_twice(recorder):
    fallback_meter = MetragenMeter(
        kind=MetragenMeterKind.WATER,
        code="AF1234",
        readings=(make_reading(2025, 12, 65.0, 5.0),),
    )
    client = _client({2025: MetragenReadings(water=(fallback_meter,), gas=())})
    await _importer(client).async_import([fallback_meter])
    assert len(_rows(recorder, CONSUMPTION_ID)) == 1


async def test_later_imports_append_only_newer_months(recorder):
    recorder.last.side_effect = lambda _hass, _n, statistic_id, *_, **__: (
        _last_row(statistic_id, 2026, 6, 100.0)
        if statistic_id == CONSUMPTION_ID
        else _last_row(statistic_id, 2026, 6, 900.0)
    )
    client = _client({})
    await _importer(client).async_import([COLD_WATER_METER])
    client.async_get_readings.assert_not_awaited()
    consumption = _rows(recorder, CONSUMPTION_ID)
    assert [row["start"] for row in consumption] == [_month_start(2026, 7)]
    assert consumption[0]["sum"] == 106.1
    cost = _rows(recorder, COST_ID)
    assert cost[0]["sum"] == 996.43


async def test_only_metadata_is_sent_when_no_month_is_newer(recorder):
    recorder.last.side_effect = lambda _hass, _n, statistic_id, *_, **__: _last_row(
        statistic_id, 2026, 7, 13.6
    )
    await _importer(_client({})).async_import([COLD_WATER_METER])
    assert _rows(recorder, CONSUMPTION_ID) == []
    assert _rows(recorder, COST_ID) == []
    assert _metadata(recorder, CONSUMPTION_ID)["name"] == "AF1234 Cold Water"


async def test_missing_cost_row_restarts_the_cost_sum(recorder):
    recorder.last.side_effect = lambda _hass, _n, statistic_id, *_, **__: (
        _last_row(statistic_id, 2026, 6, 7.5) if statistic_id == CONSUMPTION_ID else {}
    )
    await _importer(_client({})).async_import([COLD_WATER_METER])
    assert _rows(recorder, COST_ID)[0]["sum"] == 96.43


async def test_portal_error_postpones_the_import(recorder, caplog):
    client = MagicMock()
    client.async_get_readings = AsyncMock(
        side_effect=MetragenApiClientCommunicationError("down")
    )
    with caplog.at_level(logging.WARNING):
        await _importer(client).async_import([COLD_WATER_METER, GAS_METER])
    recorder.add.assert_not_called()
    assert "retrying on the next refresh" in caplog.text


async def test_history_lands_in_long_term_statistics(hass, setup_integration):
    await async_wait_recording_done(hass)
    statistic_id = "metragen:af1234_water"
    stats = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        dt_util.utc_from_timestamp(0),
        None,
        {statistic_id},
        "month",
        None,
        {"sum", "state"},
    )
    rows = stats[statistic_id]
    assert [round(row["sum"], 3) for row in rows] == [7.5, 13.6]
    assert [row["state"] for row in rows] == [80.25, 86.35]
    metadata = await get_instance(hass).async_add_executor_job(
        partial(get_metadata, hass, statistic_ids={statistic_id})
    )
    assert metadata[statistic_id][1]["name"] == "AF1234 Cold Water"
