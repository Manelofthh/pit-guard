"""Run: python examples/demo.py  (from the repo root)"""
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pit_guard import Candle, NewsItem, buy_decision, nyse_close_utc, validate_news, validate_series  # noqa: E402

UTC = timezone.utc
decision = datetime(2026, 11, 27, 17, 30, tzinfo=UTC)  # 12:30 New York, early-close day
print(f"Decision time: {decision.isoformat()}\n")


def bar(day):
    close = nyse_close_utc(day)
    return Candle("AAPL", day, 100.0, close, close + timedelta(minutes=5))


today = Candle("AAPL", date(2026, 11, 27), 101.0, nyse_close_utc(date(2026, 11, 27)), decision)
accepted, rejected = validate_series([bar(date(2026, 11, 24)), bar(date(2026, 11, 25)), today], decision)
print("Accepted sessions:", [c.session.isoformat() for c in accepted])
for key, reasons in rejected.items():
    print(f"Rejected {key}: {', '.join(reasons)}")

news = NewsItem("n1", None, decision - timedelta(minutes=10))
print("\nNews n1:", validate_news(news, decision) or "usable")

print("\nBuy AAPL, broker returns HTTP 429:", buy_decision("AAPL", lambda: (429, None)))
print("Buy AAPL, verified empty portfolio:", buy_decision("AAPL", lambda: (200, [])))
