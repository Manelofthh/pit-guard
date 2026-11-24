# pit-guard

**Stop your trading bot from lying to itself.** Two small, dependency-free guards for Python trading bots:

1. **Point-In-Time (PIT) checks** — reject any candle or headline that wasn't available yet at decision time (look-ahead bias), with an explicit reason code for every rejection.
2. **Fail-closed portfolio reads** — if the broker portfolio can't be read (HTTP 429, timeout, DNS error), every BUY is blocked. "I couldn't check" never becomes "I hold nothing".

Pure Python 3.10+, no dependencies, 27 offline tests.

```text
Decision time: 2026-11-27T17:30:00+00:00          (12:30 New York, early-close day)

Accepted sessions: ['2026-11-24', '2026-11-25']
Rejected AAPL@2026-11-27: AVAILABLE_BEFORE_CANDLE_END, INTRADAY_INCOMPLETE_DAILY_CANDLE

News n1: ['UNVERIFIABLE_PROVIDER_PUBLICATION_TIME']

Buy AAPL, broker returns HTTP 429: (False, 'PORTFOLIO_NOT_VERIFIABLE: HTTP 429, body=NoneType')
Buy AAPL, verified empty portfolio: (True, 'OK')
```

## Quick start

```bash
git clone https://github.com/Manelofthh/pit-guard.git
cd pit-guard
python -m unittest discover -s tests -t .   # 27 tests
python examples/demo.py
```

## 1. Point-In-Time checks

One rule, enforced everywhere:

```python
available_utc <= decision_utc
```

The hard part is that "available" is not the timestamp most data sources give you. A daily bar dated today
isn't complete until the session closes — at 15:30 New York its "close" is a price from the future.

```python
from datetime import date, datetime, timezone
from pit_guard import Candle, validate_candle, nyse_close_utc

day = date(2026, 11, 24)
bar = Candle("AAPL", day, 231.4, candle_end_utc=nyse_close_utc(day), available_utc=...)
reasons = validate_candle(bar, decision_utc=datetime(2026, 11, 24, 20, 30, tzinfo=timezone.utc))
# ['INTRADAY_INCOMPLETE_DAILY_CANDLE', ...]
```

| Code | Meaning |
|---|---|
| `INTRADAY_INCOMPLETE_DAILY_CANDLE` | The session hasn't closed yet at decision time |
| `CANDLE_END_UTC_MISMATCH_WITH_NYSE_CLOSE` | Bar end doesn't match the real NYSE close (early closes included) |
| `CANDLE_SESSION_IS_HOLIDAY` | Bar dated on a non-session day |
| `AVAILABLE_BEFORE_CANDLE_END` | Claims to be available before it could exist |
| `AVAILABLE_AFTER_DECISION` | You only got it after deciding |
| `STALE_DAILY_SERIES_MISSING_LATEST_SESSION` | Latest complete session missing → whole series excluded |
| `UNVERIFIABLE_PROVIDER_PUBLICATION_TIME` | News item with no verifiable publication time |
| `EVENT_AFTER_RECEIPT` | Published "after" you received it — clock or data error |
| `RETROSPECTIVE_CAPTURE_AFTER_DECISION` | News received after the decision |
| `NAIVE_DATETIME` | Timezone-less datetimes are refused |

The NYSE calendar (holidays and early closes) covers 2026–2028 from the official list. Dates outside that range
raise `CALENDAR_NOT_COVERED` instead of being guessed.

## 2. Fail-closed portfolio reads

The classic bug:

```python
def get_positions():
    try:
        r = session.get(PORTFOLIO_URL, timeout=15)
        return r.json() if r.ok else []   # HTTP 429 -> "you hold nothing"
    except Exception:
        return []                          # DNS failure -> "you hold nothing"
```

An empty list turns every duplicate check and capital limit off. With pit-guard:

```python
from pit_guard import buy_decision

def fetch():
    r = session.get(PORTFOLIO_URL, timeout=15)
    return r.status_code, r.json()

allowed, reason = buy_decision("AAPL", fetch, pending_tickers=my_submitted_not_filled)
if not allowed:
    log_blocked_order("AAPL", reason)     # audit the "no"s too
```

Exits are a different case: being unable to attempt a stop-loss is worse than missing a buy, so use
`fetch_positions(fetch, strict=False)` for sells and reporting only.

## Want the full bot?

pit-guard is extracted from the ideas behind **InversionBot V4**, a complete self-hosted trading bot template for the
**Trading 212 practice (demo) API**: Yahoo Finance PIT data layer with 30+ rejection codes, fail-closed idempotent
executor, Top-K ranking, monthly Walk-Forward optimizer with an out-of-sample adoption gate, portfolio backtester,
systemd installer and 91 offline tests.

→ **[Get InversionBot V4 (€69, one-time)](https://buy.stripe.com/7sY28k1mGgsh6LH8MJdby01)** ·
[Terms](https://gist.github.com/Manelofthh/bb6778a8ce8d3cad85d4c4ed606bf944)

## Disclaimer

Educational software. Not financial advice. No promise of returns. Trading involves substantial risk of loss.
