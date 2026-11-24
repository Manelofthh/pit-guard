"""pit-guard: Point-In-Time data checks and fail-closed portfolio reads for trading bots."""

from .calendar import nyse_close_utc, is_session
from .validate import Candle, NewsItem, validate_candle, validate_news, validate_series
from .portfolio import PortfolioUnavailableError, fetch_positions, buy_decision

__all__ = [
    "nyse_close_utc", "is_session",
    "Candle", "NewsItem", "validate_candle", "validate_news", "validate_series",
    "PortfolioUnavailableError", "fetch_positions", "buy_decision",
]
__version__ = "0.1.0"
