from datetime import datetime, timezone

import fiscal_time
from services import facturacion_service


def test_utc_night_is_previous_calendar_day_in_lima():
    utc_value = datetime(2026, 9, 21, 2, 24, tzinfo=timezone.utc)

    normalized = fiscal_time.as_lima(utc_value)

    assert normalized.isoformat() == "2026-09-20T21:24:00-05:00"


def test_naive_business_datetime_is_interpreted_as_lima():
    naive_value = datetime(2026, 9, 20, 21, 24)

    assert fiscal_time.iso_lima(naive_value) == "2026-09-20T21:24:00-05:00"


def test_all_fiscal_formatters_use_lima_offset(monkeypatch):
    utc_value = datetime(2026, 9, 21, 2, 24, tzinfo=timezone.utc)
    fixed_lima = datetime(2026, 9, 20, 21, 24, tzinfo=fiscal_time.LIMA_TZ)
    monkeypatch.setattr(fiscal_time, "now_lima", lambda: fixed_lima)

    assert facturacion_service._current_issue_datetime() == "2026-09-20T21:24:00-05:00"
    assert facturacion_service._gre_datetime(utc_value) == "2026-09-20T21:24:00-05:00"


def test_date_only_utc_midnight_preserves_calendar_date():
    date_only = datetime(2026, 4, 23, 0, 0, tzinfo=timezone.utc)

    assert fiscal_time.iso_lima_wall_time(date_only) == "2026-04-23T00:00:00-05:00"


def test_plus_minutes_preserves_lima_timezone_across_midnight():
    lima_value = datetime(2026, 9, 20, 23, 59, tzinfo=fiscal_time.LIMA_TZ)

    assert fiscal_time.iso_lima(lima_value, plus_minutes=1) == "2026-09-21T00:00:00-05:00"
