"""Fail-closed portfolio reads.

If you can't verify what you hold, you must not add risk. "I couldn't read the
portfolio" is its own state (PortfolioUnavailableError), never an empty list.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Tuple

# A fetcher returns (http_status, decoded_json_body) or raises on network errors.
Fetcher = Callable[[], Tuple[int, Any]]


class PortfolioUnavailableError(RuntimeError):
    """The broker portfolio could not be verified."""


def fetch_positions(fetch: Fetcher, *, strict: bool = True) -> list[dict]:
    """Return open positions as a list of dicts.

    strict=True (use it before any BUY): raise PortfolioUnavailableError on a
    non-2xx status, a body that isn't a list, or any exception.
    strict=False (use it for exits/reporting only): return [] on failure.
    """
    try:
        status, body = fetch()
    except Exception as exc:  # timeouts, DNS, connection resets...
        if strict:
            raise PortfolioUnavailableError(f"{type(exc).__name__}: {exc}") from exc
        return []
    if not (200 <= status < 300) or not isinstance(body, list):
        if strict:
            raise PortfolioUnavailableError(f"HTTP {status}, body={type(body).__name__}")
        return []
    return body


def buy_decision(
    ticker: str,
    fetch: Fetcher,
    *,
    pending_tickers: Iterable[str] = (),
    ticker_key: str = "ticker",
) -> tuple[bool, str]:
    """Decide whether a BUY for `ticker` may be sent. Returns (allowed, reason).

    1. Portfolio must be verifiable, otherwise -> blocked (fail-closed).
    2. Already held at the broker -> blocked.
    3. Submitted by you but not visible at the broker yet -> blocked.
    """
    try:
        positions = fetch_positions(fetch, strict=True)
    except PortfolioUnavailableError as exc:
        return False, f"PORTFOLIO_NOT_VERIFIABLE: {exc}"
    held = {str(p.get(ticker_key, "")).upper() for p in positions if isinstance(p, dict)}
    if ticker.upper() in held:
        return False, "ALREADY_HELD"
    if ticker.upper() in {t.upper() for t in pending_tickers}:
        return False, "PENDING_ORDER_NOT_YET_IN_PORTFOLIO"
    return True, "OK"
