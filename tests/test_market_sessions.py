"""Exchange-calendar boundaries for builds and latest-close recovery."""
from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from market_sessions import latest_completed_session, session_close


class MarketSessionTests(unittest.TestCase):
    def test_latest_session_accounts_for_weekends_holidays_dst_and_early_close(self):
        for now, expected in (
            ('2026-10-19T21:11', '2026-10-19'),
            ('2026-10-20T00:11', '2026-10-19'),
            ('2026-10-19T16:59', '2026-10-16'),
            ('2026-10-19T17:00', '2026-10-19'),
            ('2026-10-17T20:00', '2026-10-16'),
            ('2026-09-07T20:00', '2026-09-04'),
            ('2026-11-02T17:00', '2026-11-02'),
            ('2026-11-27T13:59', '2026-11-25'),
            ('2026-11-27T14:00', '2026-11-27'),
        ):
            with self.subTest(now=now):
                clock = datetime.fromisoformat(now).replace(tzinfo=ZoneInfo('America/New_York'))
                self.assertEqual(str(latest_completed_session(clock)), expected)

    def test_session_close_handles_dst_and_half_day(self):
        for day, utc_hour in (('2026-10-19', 20), ('2026-11-02', 21), ('2026-11-27', 18)):
            self.assertEqual(session_close(datetime.fromisoformat(day).date()).hour, utc_hour)
        with self.assertRaisesRegex(ValueError, '不是 NASDAQ 交易日'):
            session_close(datetime(2026, 11, 26).date())
