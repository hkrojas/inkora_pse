"""Authoritative clock for Peruvian fiscal documents.

Inkora runs on infrastructure that commonly uses UTC. Fiscal timestamps,
however, are issued in Peru time (UTC-05:00) and must not depend on the host
timezone. Database columns are currently timezone-naive, so helpers expose
both aware values for provider payloads and naive Lima wall-clock values for
persistence.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


LIMA_TZ = timezone(timedelta(hours=-5), name="America/Lima")


def now_lima() -> datetime:
    """Return the current aware datetime in Lima."""

    return datetime.now(LIMA_TZ)


def now_lima_naive() -> datetime:
    """Return the current Lima wall-clock time for naive DateTime columns."""

    return now_lima().replace(tzinfo=None)


def today_lima() -> date:
    return now_lima().date()


def as_lima(value: datetime | None = None) -> datetime:
    """Normalize a datetime to Lima.

    Naive values in Inkora represent local business time, so they are attached
    to Lima instead of being interpreted in the server's timezone.
    """

    if value is None:
        return now_lima()
    if value.tzinfo is None:
        return value.replace(tzinfo=LIMA_TZ)
    return value.astimezone(LIMA_TZ)


def iso_lima(value: datetime | None = None, *, plus_minutes: int = 0) -> str:
    normalized = as_lima(value)
    if plus_minutes:
        normalized += timedelta(minutes=plus_minutes)
    return normalized.replace(microsecond=0).isoformat()


def iso_lima_wall_time(value: datetime | None = None, *, plus_minutes: int = 0) -> str:
    """Format a business-entered calendar value with the Lima offset.

    Date-only fields historically arrive as UTC-midnight datetimes. They are
    calendar values, not instants, so converting them would move them to the
    previous date. Preserve their displayed components and attach UTC-05:00.
    """

    if value is None:
        normalized = now_lima()
    else:
        normalized = value.replace(tzinfo=LIMA_TZ)
    if plus_minutes:
        normalized += timedelta(minutes=plus_minutes)
    return normalized.replace(microsecond=0).isoformat()
