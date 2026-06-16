"""US equity market (NYSE/Nasdaq) trading-day helpers.

Used to compute the *next valid trading day* for a prediction so a report never
targets a weekend or market holiday. Weekends are always skipped; US market
holidays are skipped when ``pandas`` is available (it is a transitive
dependency), otherwise only weekends are skipped.
"""

from datetime import date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

US_EASTERN = ZoneInfo("America/New_York")
MARKET_CLOSE_HOUR = 16  # 4:00 PM ET — regular session close

try:
    from pandas.tseries.holiday import (
        AbstractHolidayCalendar,
        Holiday,
        nearest_workday,
        USMartinLutherKingJr,
        USPresidentsDay,
        GoodFriday,
        USMemorialDay,
        USLaborDay,
        USThanksgivingDay,
    )

    _PANDAS_AVAILABLE = True
except Exception:  # pragma: no cover
    _PANDAS_AVAILABLE = False


if _PANDAS_AVAILABLE:

    class _NYSEHolidayCalendar(AbstractHolidayCalendar):
        """Approximate NYSE holiday calendar (regular full-day closures)."""

        rules = [
            Holiday("New Year's Day", month=1, day=1, observance=nearest_workday),
            USMartinLutherKingJr,
            USPresidentsDay,
            GoodFriday,
            USMemorialDay,
            Holiday(
                "Juneteenth",
                month=6,
                day=19,
                start_date=datetime(2022, 1, 1),
                observance=nearest_workday,
            ),
            Holiday("Independence Day", month=7, day=4, observance=nearest_workday),
            USLaborDay,
            USThanksgivingDay,
            Holiday("Christmas Day", month=12, day=25, observance=nearest_workday),
        ]

    _CALENDAR = _NYSEHolidayCalendar()

    @lru_cache(maxsize=16)
    def _holidays_for_year(year: int) -> frozenset:
        days = _CALENDAR.holidays(start=f"{year}-01-01", end=f"{year}-12-31")
        return frozenset(d.date() for d in days)

else:  # pragma: no cover

    @lru_cache(maxsize=16)
    def _holidays_for_year(year: int) -> frozenset:
        return frozenset()


def _as_date(d) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return datetime.strptime(d, "%Y-%m-%d").date()
    raise TypeError(f"Unsupported date type: {type(d)!r}")


def is_trading_day(d) -> bool:
    """True if ``d`` is a weekday and not a US market holiday."""
    d = _as_date(d)
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return d not in _holidays_for_year(d.year)


def next_trading_day(d) -> date:
    """Return the first valid trading day strictly after ``d``."""
    d = _as_date(d)
    nxt = d + timedelta(days=1)
    while not is_trading_day(nxt):
        nxt += timedelta(days=1)
    return nxt


def previous_trading_day(d) -> date:
    """Return the most recent valid trading day strictly before ``d``."""
    d = _as_date(d)
    prev = d - timedelta(days=1)
    while not is_trading_day(prev):
        prev -= timedelta(days=1)
    return prev


def now_eastern() -> datetime:
    """Current wall-clock time in US/Eastern (NYSE regular session timezone)."""
    return datetime.now(US_EASTERN)


def required_market_data_date(as_of: datetime | None = None) -> date:
    """Return the trading date whose daily OHLC bar must be present at run time.

    - After 4:00 PM ET on a trading day → today's completed session bar.
    - Before 4:00 PM ET on a trading day → previous trading day's bar.
    - Weekend / market holiday → previous trading day's bar.
    """
    as_of = as_of or now_eastern()
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=US_EASTERN)
    else:
        as_of = as_of.astimezone(US_EASTERN)

    today = as_of.date()
    if not is_trading_day(today):
        return previous_trading_day(today)
    if as_of.hour > MARKET_CLOSE_HOUR or (
        as_of.hour == MARKET_CLOSE_HOUR and as_of.minute >= 0
    ):
        return today
    return previous_trading_day(today)


if __name__ == "__main__":
    for s in ["2026-06-12", "2026-06-13", "2026-06-15", "2026-07-03", "2026-12-24"]:
        print(f"{s} ({_as_date(s).strftime('%A')}) -> next trading day "
              f"{next_trading_day(s)} ({next_trading_day(s).strftime('%A')})")
