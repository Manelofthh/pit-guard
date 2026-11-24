import unittest

from pit_guard.portfolio import PortfolioUnavailableError, buy_decision, fetch_positions


def ok(body):
    return lambda: (200, body)


def status(code):
    return lambda: (code, {"error": "x"})


def boom(exc):
    def f():
        raise exc
    return f


class FetchTests(unittest.TestCase):
    def test_strict_raises_on_429(self):
        with self.assertRaises(PortfolioUnavailableError):
            fetch_positions(status(429))

    def test_strict_raises_on_network_error(self):
        with self.assertRaises(PortfolioUnavailableError):
            fetch_positions(boom(TimeoutError("read timed out")))

    def test_strict_raises_on_non_list_body(self):
        with self.assertRaises(PortfolioUnavailableError):
            fetch_positions(ok({"items": []}))

    def test_non_strict_returns_empty_for_exits_only(self):
        self.assertEqual(fetch_positions(status(503), strict=False), [])


class BuyDecisionTests(unittest.TestCase):
    def test_buy_blocked_on_429(self):
        allowed, reason = buy_decision("AAPL", status(429))
        self.assertFalse(allowed)
        self.assertTrue(reason.startswith("PORTFOLIO_NOT_VERIFIABLE"))

    def test_buy_blocked_on_dns_error(self):
        allowed, reason = buy_decision("AAPL", boom(OSError("Name or service not known")))
        self.assertFalse(allowed)
        self.assertTrue(reason.startswith("PORTFOLIO_NOT_VERIFIABLE"))

    def test_buy_blocked_when_already_held(self):
        self.assertEqual(buy_decision("aapl", ok([{"ticker": "AAPL"}])), (False, "ALREADY_HELD"))

    def test_buy_blocked_when_pending(self):
        self.assertEqual(
            buy_decision("MSFT", ok([]), pending_tickers=["msft"]),
            (False, "PENDING_ORDER_NOT_YET_IN_PORTFOLIO"),
        )

    def test_buy_allowed_on_verified_empty_portfolio(self):
        self.assertEqual(buy_decision("AAPL", ok([])), (True, "OK"))


if __name__ == "__main__":
    unittest.main()
