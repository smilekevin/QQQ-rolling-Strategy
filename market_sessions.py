"""NASDAQ sessions and the one-hour post-close publication boundary."""
from datetime import datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal


MARKET_TZ = ZoneInfo("America/New_York")


@lru_cache(maxsize=1)
def calendar():
    return mcal.get_calendar("NASDAQ")


@lru_cache(maxsize=32)
def session_close(day):
    schedule = calendar().schedule(start_date=day, end_date=day)
    if schedule.empty:
        raise ValueError(f"{day} 不是 NASDAQ 交易日")
    return schedule.iloc[-1]["market_close"].to_pydatetime()


def latest_completed_session(now=None):
    now = now or datetime.now(MARKET_TZ)
    day = now.astimezone(MARKET_TZ).date()
    schedule = calendar().schedule(start_date=day - timedelta(days=14), end_date=day)
    ready = schedule[schedule["market_close"] + timedelta(hours=1) <= now]
    if ready.empty:
        raise ValueError("最近 14 天没有可验证的已收盘交易日")
    return ready.index[-1].date()
