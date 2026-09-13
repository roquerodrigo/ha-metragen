from __future__ import annotations

from datetime import date

import pytest

from custom_components.metragen.data import MetragenMeter, MetragenMeterKind

from .conftest import COLD_WATER_METER, GAS_METER, HOT_WATER_METER, make_reading


def _meter(kind=MetragenMeterKind.WATER, code="AF2616", readings=()):
    return MetragenMeter(kind=kind, code=code, readings=tuple(readings))


def test_key_combines_kind_and_slugified_code():
    assert COLD_WATER_METER.key == "water_af2616"
    assert GAS_METER.key == "gas_aq2616"


def test_latest_is_the_last_reading():
    assert COLD_WATER_METER.latest == COLD_WATER_METER.readings[-1]


def test_latest_is_none_without_readings():
    assert _meter().latest is None


def test_yearly_consumption_sums_only_the_year_of_the_latest_reading():
    meter = _meter(
        readings=[
            make_reading(2025, 12, 10.0, 5.0),
            make_reading(2026, 1, 11.5, 1.5),
            make_reading(2026, 2, 13.75, 2.25),
        ]
    )
    assert meter.yearly_consumption == 3.75


def test_yearly_consumption_is_zero_without_readings():
    assert _meter().yearly_consumption == 0.0


@pytest.mark.parametrize(
    ("meter", "expected"),
    [
        (COLD_WATER_METER, "cold_water_meter"),
        (HOT_WATER_METER, "hot_water_meter"),
        (GAS_METER, "gas_meter"),
        (_meter(code="af12"), "cold_water_meter"),
        (_meter(code="XY99"), "water_meter"),
        (_meter(kind=MetragenMeterKind.GAS, code="AF1"), "gas_meter"),
    ],
)
def test_device_translation_key_follows_the_meter_code_prefix(meter, expected):
    assert meter.device_translation_key == expected


def test_reading_period_start_is_the_first_day_of_the_month():
    assert make_reading(2026, 7, 1.0, 1.0).period_start == date(2026, 7, 1)
