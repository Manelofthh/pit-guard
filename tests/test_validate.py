import unittest
from datetime import date, datetime, timedelta, timezone

from pit_guard.calendar import nyse_close_utc
from pit_guard.validate import Candle, NewsItem, validate_candle, validate_news, validate_series

UTC = timezone.utc


def candle(day, *, end=None, available=None, ticker="AAPL"):
    close = nyse_close_utc(day)
    return Candle(ticker, day, 100.0, end or close, available or close + timedelta(minutes=5))


class CandleTests(unittest.TestCase):
    def test_complete_candle_is_usable(self):
        decision = datetime(2026, 11, 25, 15, 0, tzinfo=UTC)
        self.assertEqual(validate_candle(candle(date(2026, 11, 24)), decision), [])

    def test_intraday_incomplete_daily_candle(self):
        decision = datetime(2026, 11, 24, 20, 30, tzinfo=UTC)  # 15:30 New York, before the close
        day = date(2026, 11, 24)
        c = Candle("AAPL", day, 100.0, nyse_close_utc(day), decision - timedelta(minutes=1))
        self.assertIn("INTRADAY_INCOMPLETE_DAILY_CANDLE", validate_candle(c, decision))

    def test_candle_end_must_match_official_close(self):
        day = date(2026, 11, 27)  # early close: 13:00 New York
        wrong_end = datetime(2026, 11, 27, 21, 0, tzinfo=UTC)  # assumed 16:00
        c = candle(day, end=wrong_end, available=wrong_end)
        decision = datetime(2026, 11, 30, 15, 0, tzinfo=UTC)
        self.assertIn("CANDLE_END_UTC_MISMATCH_WITH_NYSE_CLOSE", validate_candle(c, decision))

    def test_holiday_session(self):
        fake = Candle("AAPL", date(2026, 11, 26), 1.0,
                      datetime(2026, 11, 26, 21, tzinfo=UTC), datetime(2026, 11, 26, 21, tzinfo=UTC))
        decision = datetime(2026, 11, 30, 15, tzinfo=UTC)
        self.assertEqual(validate_candle(fake, decision), ["CANDLE_SESSION_IS_HOLIDAY"])

    def test_available_after_decision(self):
        day = date(2026, 11, 24)
        decision = datetime(2026, 11, 24, 21, 1, tzinfo=UTC)
        c = candle(day, available=datetime(2026, 11, 24, 21, 30, tzinfo=UTC))
        self.assertEqual(validate_candle(c, decision), ["AVAILABLE_AFTER_DECISION"])

    def test_naive_datetimes_rejected(self):
        day = date(2026, 11, 24)
        c = Candle("AAPL", day, 1.0, datetime(2026, 11, 24, 21), datetime(2026, 11, 24, 21, 5))
        self.assertEqual(validate_candle(c, datetime(2026, 11, 25, tzinfo=UTC)), ["NAIVE_DATETIME"])


class NewsTests(unittest.TestCase):
    decision = datetime(2026, 11, 24, 18, 0, tzinfo=UTC)

    def test_usable_news(self):
        n = NewsItem("1", datetime(2026, 11, 24, 17, tzinfo=UTC), datetime(2026, 11, 24, 17, 2, tzinfo=UTC))
        self.assertEqual(validate_news(n, self.decision), [])

    def test_unverifiable_publication_time(self):
        n = NewsItem("2", None, datetime(2026, 11, 24, 17, tzinfo=UTC))
        self.assertEqual(validate_news(n, self.decision), ["UNVERIFIABLE_PROVIDER_PUBLICATION_TIME"])

    def test_event_after_receipt(self):
        n = NewsItem("3", datetime(2026, 11, 24, 17, 30, tzinfo=UTC), datetime(2026, 11, 24, 17, tzinfo=UTC))
        self.assertIn("EVENT_AFTER_RECEIPT", validate_news(n, self.decision))

    def test_retrospective_capture(self):
        n = NewsItem("4", datetime(2026, 11, 24, 17, tzinfo=UTC), datetime(2026, 11, 24, 19, tzinfo=UTC))
        self.assertIn("RETROSPECTIVE_CAPTURE_AFTER_DECISION", validate_news(n, self.decision))


class SeriesTests(unittest.TestCase):
    def test_series_ok(self):
        decision = datetime(2026, 11, 25, 15, 0, tzinfo=UTC)
        accepted, rejected = validate_series([candle(date(2026, 11, 23)), candle(date(2026, 11, 24))], decision)
        self.assertEqual([c.session for c in accepted], [date(2026, 11, 23), date(2026, 11, 24)])
        self.assertEqual(rejected, {})

    def test_stale_series_rejected_entirely(self):
        decision = datetime(2026, 11, 25, 15, 0, tzinfo=UTC)  # latest complete session: 24 Nov
        accepted, rejected = validate_series([candle(date(2026, 11, 20)), candle(date(2026, 11, 23))], decision)
        self.assertEqual(accepted, [])
        self.assertEqual(rejected["AAPL@series"], ["STALE_DAILY_SERIES_MISSING_LATEST_SESSION"])

    def test_todays_incomplete_bar_dropped_but_series_ok(self):
        decision = datetime(2026, 11, 25, 15, 0, tzinfo=UTC)  # 10:00 New York
        today = Candle("AAPL", date(2026, 11, 25), 1.0, nyse_close_utc(date(2026, 11, 25)), decision)
        accepted, rejected = validate_series([candle(date(2026, 11, 24)), today], decision)
        self.assertEqual([c.session for c in accepted], [date(2026, 11, 24)])
        self.assertIn("INTRADAY_INCOMPLETE_DAILY_CANDLE", rejected["AAPL@2026-11-25"])


if __name__ == "__main__":
    unittest.main()
