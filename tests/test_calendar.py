import unittest
from datetime import date, datetime, timezone

from pit_guard.calendar import is_session, nyse_close_utc, previous_session

UTC = timezone.utc


class CalendarTests(unittest.TestCase):
    def test_regular_close_winter_and_summer(self):
        self.assertEqual(nyse_close_utc(date(2026, 11, 24)), datetime(2026, 11, 24, 21, 0, tzinfo=UTC))
        self.assertEqual(nyse_close_utc(date(2026, 7, 1)), datetime(2026, 7, 1, 20, 0, tzinfo=UTC))

    def test_early_close(self):
        self.assertEqual(nyse_close_utc(date(2026, 11, 27)), datetime(2026, 11, 27, 18, 0, tzinfo=UTC))

    def test_holiday_and_weekend_are_not_sessions(self):
        self.assertFalse(is_session(date(2026, 11, 26)))  # Thanksgiving
        self.assertFalse(is_session(date(2026, 11, 28)))  # Saturday
        with self.assertRaises(ValueError):
            nyse_close_utc(date(2026, 11, 26))

    def test_uncovered_year_is_not_guessed(self):
        with self.assertRaisesRegex(ValueError, "CALENDAR_NOT_COVERED"):
            is_session(date(2030, 1, 2))

    def test_previous_session_skips_holiday(self):
        self.assertEqual(previous_session(date(2026, 11, 27)), date(2026, 11, 25))


if __name__ == "__main__":
    unittest.main()
