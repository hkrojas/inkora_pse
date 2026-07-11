"""Fiscal timestamps must follow Peru's legal operating date, not server UTC."""
from datetime import datetime, timedelta, timezone


# Peru has no daylight-saving changes; a fixed UTC-5 offset keeps the fiscal
# clock portable in Windows development environments that lack IANA tzdata.
PERU_TIMEZONE = timezone(timedelta(hours=-5), name="America/Lima")


def now_in_peru() -> datetime:
    return datetime.now(PERU_TIMEZONE)


def now_in_peru_naive() -> datetime:
    """Return Peru wall time for legacy timestamp-without-time-zone columns."""
    return now_in_peru().replace(tzinfo=None)


def fiscal_datetime_in_peru(value: datetime | None = None) -> datetime:
    """Interpret persisted naive fiscal values as Peru local wall time."""
    if value is None:
        return now_in_peru()
    if value.tzinfo is None:
        return value.replace(tzinfo=PERU_TIMEZONE)
    return value.astimezone(PERU_TIMEZONE)


def fiscal_today():
    return now_in_peru().date()
