"""Regression coverage for asynchronous Yahoo daily-bar publication."""
from contextlib import redirect_stdout
from datetime import datetime
import io
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from scripts.build_report import validate_prices


ROOT = Path(__file__).resolve().parents[1]
OHLC = ['Open', 'High', 'Low', 'Close']


def source_prices():
    dates = pd.bdate_range('1997-01-02', '2026-10-15', name='Date')
    close = pd.Series(100 + np.arange(len(dates)) * .1
                      + np.sin(np.arange(len(dates))), index=dates)
    frame = pd.DataFrame({'Open': close * .999, 'High': close * 1.01,
                          'Low': close * .99, 'Close': close, 'Volume': 1000})
    frames = {'^NDX': frame, 'QQQ': frame.loc['1999-03-10':].copy(),
              'QLD': frame.loc['2006-06-21':].copy(),
              '^IRX': frame.assign(Close=4.), '^VIX': frame.assign(Close=20.)}
    for ticker, data in frames.items():
        data.columns = pd.MultiIndex.from_product([data.columns, [ticker]],
                                                  names=['Price', 'Ticker'])
    return frames


def prepare(frames, work):
    fake_yf = types.ModuleType('yfinance')
    fake_yf.download = lambda ticker, **kwargs: frames[ticker].copy()
    namespace = {'__file__': str(work / '1_prepare_data.py')}
    with patch.dict('sys.modules', {'yfinance': fake_yf}), redirect_stdout(io.StringIO()):
        exec(compile((ROOT / '1_prepare_data.py').read_text(),
                     str(ROOT / '1_prepare_data.py'), 'exec'), namespace)
    return pd.read_csv(work / 'prices.csv', index_col='Date', parse_dates=True)


class PrepareDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        # Freeze the New York clock so date validation does not age with the fixture.
        self.clock = patch('scripts.build_report.datetime')
        clock = self.clock.start()
        self.addCleanup(self.clock.stop)
        clock.now.return_value = datetime(2026, 10, 16, 20, tzinfo=ZoneInfo('America/New_York'))

    def test_volume_only_tail_matches_healthy_export_exactly(self):
        frames = source_prices()
        expected = prepare(frames, self.work)
        # NDX has the next day's actual prices, ETFs only have volume.
        for ticker, frame in frames.items():
            frame.loc[pd.Timestamp('2026-10-16')] = frame.iloc[-1]
            if ticker in ('QQQ', 'QLD'):
                frame.loc[pd.Timestamp('2026-10-16'), OHLC] = np.nan
        actual = prepare(frames, self.work)
        pd.testing.assert_frame_equal(actual, expected)
        self.assertEqual(validate_prices(self.work / 'prices.csv'), '2026-10-15')
        # Warm-up prices never become executable returns; segment compounding stays exact.
        self.assertTrue(actual.loc[:'1999-03-09', [
            'qqq_overnight_ret', 'qqq_intraday_ret',
            'qld_overnight_ret', 'qld_intraday_ret']].isna().all().all())
        for ticker in ('qqq', 'qld'):
            rebuilt = ((1 + actual[f'{ticker}_overnight_ret'])
                       * (1 + actual[f'{ticker}_intraday_ret']) - 1)
            np.testing.assert_allclose(rebuilt, actual[f'{ticker}_ret'], atol=1e-10)

    def test_qqq_can_extend_beyond_ndx_and_ndx_never_fills_listing_gaps(self):
        frames = source_prices()
        frames['^NDX'] = frames['^NDX'].iloc[:-1]
        frames['QQQ'] = frames['QQQ'].drop(pd.Timestamp('2026-10-13'))
        actual = prepare(frames, self.work)
        self.assertEqual(actual.index[-1], pd.Timestamp('2026-10-15'))
        self.assertNotIn(pd.Timestamp('2026-10-13'), actual.index)
        np.testing.assert_allclose(actual.loc['1999-03-10':, 'signal_close'],
                                   frames['QQQ'][('Close', 'QQQ')])

    def test_ndx_empty_tail_does_not_extend_the_report(self):
        frames = source_prices()
        frames['^NDX'].loc[pd.Timestamp('2026-10-16')] = np.nan
        actual = prepare(frames, self.work)
        self.assertEqual(actual.index[-1], pd.Timestamp('2026-10-15'))

    def test_partially_missing_latest_bar_is_still_rejected(self):
        frames = source_prices()
        frames['QQQ'].loc[pd.Timestamp('2026-10-15'), 'High'] = np.nan
        actual = prepare(frames, self.work)
        self.assertEqual(actual.index[-1], pd.Timestamp('2026-10-15'))
        with self.assertRaisesRegex(ValueError, '2026-10-15.*signal_high'):
            validate_prices(self.work / 'prices.csv')

    def test_no_downloaded_prices_fails_clearly(self):
        for ticker in ('^NDX', 'QQQ', 'QLD'):
            for empty in (False, True):
                with self.subTest(ticker=ticker, empty=empty):
                    frames = source_prices()
                    if empty:
                        frames[ticker] = frames[ticker].iloc[:0]
                    else:
                        frames[ticker].loc[:, OHLC] = np.nan
                    with self.assertRaisesRegex(ValueError, '未下载到有效价格'):
                        prepare(frames, self.work)

    def test_invalid_latest_price_diagnostics_include_date_and_column(self):
        actual = prepare(source_prices(), self.work)
        for value in ('', 'invalid', 'NaN', 'inf', '0', '-1'):
            with self.subTest(value=value):
                changed = actual.astype({'qqq': object})
                changed.loc[changed.index[-1], 'qqq'] = value
                changed.to_csv(self.work / 'prices.csv')
                with self.assertRaisesRegex(ValueError, '2026-10-15.*qqq'):
                    validate_prices(self.work / 'prices.csv')

    def test_date_safety_checks_still_reject_stale_future_and_early_bars(self):
        prepare(source_prices(), self.work)
        for now, message in ((datetime(2026, 10, 14, 20), '晚于'),
                             (datetime(2026, 10, 15, 16), '17:00'),
                             (datetime(2026, 10, 23, 20), '7 个自然日')):
            with self.subTest(now=now):
                with patch('scripts.build_report.datetime') as clock:
                    clock.now.return_value = now.replace(tzinfo=ZoneInfo('America/New_York'))
                    with self.assertRaisesRegex(ValueError, message):
                        validate_prices(self.work / 'prices.csv')


if __name__ == '__main__':
    unittest.main()
