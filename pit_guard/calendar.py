"""Minimal NYSE regular-session calendar (2026-2028, from the official NYSE holiday list).

Dates outside the covered years raise ValueError instead of guessing: an unknown
calendar is treated as "not verifiable", never as "normal day".
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
COVERED_YEARS = (2026, 2027, 2028)

HOLIDAYS = frozenset(
    date.fromisoformat(d)
    for d in (
        "2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 2026-06-19 2026-07-03 "
        "2026-09-07 2026-11-26 2026-12-25 2027-01-01 2027-01-18 2027-02-15 2027-03-26 "
        "2027-05-31 2027-06-18 2027-07-05 2027-09-06 2027-11-25 2027-12-24 2028-01-17 "
        "2028-02-21 2028-04-14 2028-05-29 2028-06-19 2028-07-04 2028-09-04 2028-11-23 "
        "2028-12-25"
    ).split()
)
EARLY_CLOSES = frozenset(
    date.fromisoformat(d)
    for d in "2026-11-27 2026-12-24 2027-11-26 2028-07-03 2028-11-24".split()
)


def _check_covered(day: date) -> None:
    if day.year not in COVERED_YEARS:
        raise ValueError(f"CALENDAR_NOT_COVERED:{day.isoformat()}")


def is_session(day: date) -> bool:
    """True if `day` is a regular NYSE trading session."""
    _check_covered(day)
    return day.weekday() < 5 and day not in HOLIDAYS


def nyse_close_utc(day: date) -> datetime:
    """Official close of the session `day` as an aware UTC datetime (13:00 NY on early closes)."""
    if not is_session(day):
        raise ValueError(f"NOT_A_SESSION:{day.isoformat()}")
    close = time(13) if day in EARLY_CLOSES else time(16)
    return datetime.combine(day, close, tzinfo=NY).astimezone(timezone.utc)


def previous_session(day: date) -> date:
    """Latest session strictly before `day`."""
    from datetime import timedelta

    d = day - timedelta(days=1)
    while not is_session(d):
        d -= timedelta(days=1)
    return d
