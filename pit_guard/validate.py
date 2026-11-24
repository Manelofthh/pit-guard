"""Point-In-Time checks.

One rule: a data point may be used for a decision only if it was *available*
at decision time (available_utc <= decision_utc). Every check returns explicit
reason codes; an empty list means "usable". Nothing is silently dropped or fixed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Optional

from .calendar import is_session, nyse_close_utc, previous_session


@dataclass(frozen=True)
class Candle:
    ticker: str
    session: date              # trading day the bar belongs to
    close: float
    candle_end_utc: datetime   # when the bar is complete (official close)
    available_utc: datetime    # when *you* could first have seen it


@dataclass(frozen=True)
class NewsItem:
    item_id: str
    published_utc: Optional[datetime]  # provider's publication time; None = unknown
    received_utc: datetime             # when your system received it


def _aware(*values: Optional[datetime]) -> bool:
    return all(v is None or v.tzinfo is not None for v in values)


def validate_candle(candle: Candle, decision_utc: datetime) -> list[str]:
    """Reason codes why `candle` can't be used at `decision_utc` (empty list = usable)."""
    if not _aware(candle.candle_end_utc, candle.available_utc, decision_utc):
        return ["NAIVE_DATETIME"]
    try:
        if not is_session(candle.session):
            return ["CANDLE_SESSION_IS_HOLIDAY"]
        official_close = nyse_close_utc(candle.session)
    except ValueError as exc:
        return [str(exc).split(":")[0]]

    reasons: list[str] = []
    if candle.candle_end_utc != official_close:
        reasons.append("CANDLE_END_UTC_MISMATCH_WITH_NYSE_CLOSE")
    if candle.available_utc < official_close:
        reasons.append("AVAILABLE_BEFORE_CANDLE_END")
    if decision_utc < official_close:
        reasons.append("INTRADAY_INCOMPLETE_DAILY_CANDLE")
    if candle.available_utc > decision_utc:
        reasons.append("AVAILABLE_AFTER_DECISION")
    return reasons


def validate_news(item: NewsItem, decision_utc: datetime) -> list[str]:
    """Reason codes why `item` can't be used at `decision_utc` (empty list = usable)."""
    if not _aware(item.published_utc, item.received_utc, decision_utc):
        return ["NAIVE_DATETIME"]
    reasons: list[str] = []
    if item.published_utc is None:
        reasons.append("UNVERIFIABLE_PROVIDER_PUBLICATION_TIME")
    elif item.published_utc > item.received_utc:
        reasons.append("EVENT_AFTER_RECEIPT")
    if item.received_utc > decision_utc:
        reasons.append("RETROSPECTIVE_CAPTURE_AFTER_DECISION")
    return reasons


def latest_complete_session(decision_utc: datetime) -> date:
    """Most recent session whose official close is at or before `decision_utc`."""
    from .calendar import NY

    day = decision_utc.astimezone(NY).date()
    if is_session(day) and nyse_close_utc(day) <= decision_utc:
        return day
    return previous_session(day)


def validate_series(candles: Iterable[Candle], decision_utc: datetime) -> tuple[list[Candle], dict[str, list[str]]]:
    """Split a daily series into usable candles and rejections.

    Returns (accepted, rejected) where `rejected` maps "<ticker>@<session>" to its
    reason codes. If the latest complete session is missing from the accepted
    candles, the whole series is stale and nothing is accepted.
    """
    accepted: list[Candle] = []
    rejected: dict[str, list[str]] = {}
    ticker = None
    for c in candles:
        ticker = ticker or c.ticker
        reasons = validate_candle(c, decision_utc)
        if reasons:
            rejected[f"{c.ticker}@{c.session.isoformat()}"] = reasons
        else:
            accepted.append(c)

    expected = latest_complete_session(decision_utc)
    if not any(c.session == expected for c in accepted):
        key = f"{ticker or '?'}@series"
        rejected[key] = ["STALE_DAILY_SERIES_MISSING_LATEST_SESSION"]
        return [], rejected
    return sorted(accepted, key=lambda c: c.session), rejected
