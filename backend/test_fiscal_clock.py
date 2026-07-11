from datetime import datetime, timezone

from services import facturacion_service
from services.fiscal_clock import fiscal_datetime_in_peru


def test_fiscal_datetime_converts_utc_to_peru_before_building_xml_date():
    utc_timestamp = datetime(2026, 7, 11, 0, 11, 1, tzinfo=timezone.utc)

    localized = fiscal_datetime_in_peru(utc_timestamp)

    assert localized.isoformat() == "2026-07-10T19:11:01-05:00"
    assert facturacion_service._current_issue_datetime(utc_timestamp) == "2026-07-10T19:11:01-05:00"


def test_fiscal_datetime_treats_legacy_naive_values_as_peru_wall_time():
    legacy_value = datetime(2026, 7, 10, 19, 11, 1)

    assert fiscal_datetime_in_peru(legacy_value).isoformat() == "2026-07-10T19:11:01-05:00"
