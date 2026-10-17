"""Regression coverage for asynchronous Yahoo daily-bar publication."""
from contextlib import redirect_stdout
from copy import deepcopy
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


def closing_sources():
    frames = source_prices()
    raw_frames = {}
    metadata = {}
    end = int(datetime(2026, 10, 16, 16, tzinfo=ZoneInfo('America/New_York')).timestamp())
    for ticker, frame in frames.items():
        frame.loc[pd.Timestamp('2026-10-16')] = frame.iloc[-1]
        if ticker in ('QQQ', 'QLD'):
            close = float(frame[('Close', ticker)].iloc[-1]) * .975
            frame.loc[pd.Timestamp('2026-10-16'), 'Close'] = close
            frame.loc[pd.Timestamp('2026-10-16'), 'Low'] = close * .99
            raw = frame.xs(ticker, axis=1, level='Ticker').tail(5).copy()
            raw['Adj Close'] = raw['Close']
            raw[['Dividends', 'Stock Splits', 'Capital Gains']] = 0.
            raw.loc[raw.index[-1], ['Close', 'Adj Close']] = np.nan
            raw_frames[ticker] = raw
            metadata[ticker] = {'symbol': ticker, 'currency': 'USD',
                                'exchangeTimezoneName': 'America/New_York',
                                'regularMarketTime': end, 'regularMarketPrice': close,
                                'currentTradingPeriod': {'regular': {'end': end}}}
    return frames, raw_frames, metadata


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 16, 20, tzinfo=ZoneInfo('America/New_York')).astimezone(tz)


def downloader(fake_yf=None):
    namespace = {'__file__': str(ROOT / '1_prepare_data.py')}
    source = (ROOT / '1_prepare_data.py').read_text().split('# ---- 下载 ----')[0]
    with patch.dict('sys.modules', {'yfinance': fake_yf or types.ModuleType('yfinance')}):
        exec(compile(source, str(ROOT / '1_prepare_data.py'), 'exec'), namespace)
    namespace['datetime'] = FixedDateTime
    return namespace


def prepare(frames, work, raw_frames=None, metadata=None):
    fake_yf = types.ModuleType('yfinance')
    fake_yf.download = lambda ticker, **kwargs: frames[ticker].copy()
    fake_yf.Ticker = lambda ticker: types.SimpleNamespace(
        history=lambda **kwargs: (raw_frames or {}).get(ticker, pd.DataFrame()).copy(),
        get_history_metadata=lambda: (metadata or {}).get(ticker, {}))
    namespace = downloader(fake_yf)
    namespace['OUT'] = str(work) + '/'
    with patch.dict('sys.modules', {'yfinance': fake_yf}), redirect_stdout(io.StringIO()):
        exec(compile((ROOT / '1_prepare_data.py').read_text().split('# ---- 下载 ----')[1],
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
        for ticker in ('QQQ', 'QLD'):
            with self.subTest(ticker=ticker):
                frames = source_prices()
                frames[ticker].loc[pd.Timestamp('2026-10-15'), 'High'] = np.nan
                with self.assertRaisesRegex(ValueError, f'{ticker}.*2026-10-15.*High'):
                    prepare(frames, self.work)

    def test_verified_regular_close_recovers_only_latest_bar(self):
        frames, raw, metadata = closing_sources()
        expected = prepare(frames, self.work)
        for ticker in ('QQQ', 'QLD'):
            frames[ticker].loc[pd.Timestamp('2026-10-16'), OHLC] = np.nan
        actual = prepare(frames, self.work, raw, metadata)
        # Exactly matches an ordinary complete Yahoo daily-bar export, including history.
        pd.testing.assert_frame_equal(actual, expected)
        self.assertEqual(validate_prices(self.work / 'prices.csv'), '2026-10-16')

    def test_failed_or_wrong_symbol_quote_keeps_common_complete_cutoff(self):
        frames, raw, metadata = closing_sources()
        expected = prepare(source_prices(), self.work)
        for ticker in ('QQQ', 'QLD'):
            frames[ticker].loc[pd.Timestamp('2026-10-16'), OHLC] = np.nan
        # QQQ recovers but QLD's mismatched quote cannot become synthetic post-listing QLD.
        metadata['QLD']['symbol'] = 'TQQQ'
        actual = prepare(frames, self.work, raw, metadata)
        pd.testing.assert_frame_equal(actual, expected)

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


class RegularCloseTests(unittest.TestCase):
    def setUp(self):
        _, raw, metadata = closing_sources()
        self.raw = raw['QQQ']
        self.metadata = metadata['QQQ']
        self.recover = downloader()['regular_close_bar']
        self.date = datetime(2026, 10, 16).date()

    def test_rejects_intraday_afterhours_stale_or_invalid_quotes(self):
        for change in ({'regularMarketTime': self.metadata['regularMarketTime'] - 1},
                       {'regularMarketTime': self.metadata['regularMarketTime'] + 1},
                       {'regularMarketTime': self.metadata['regularMarketTime'] - 86400},
                       {'regularMarketPrice': float('nan')}, {'regularMarketPrice': 0},
                       {'regularMarketPrice': float('inf')}, {'regularMarketPrice': 'invalid'},
                       {'regularMarketPrice': 1e9}, {'currency': 'CAD'},
                       {'exchangeTimezoneName': 'UTC'}, {'currentTradingPeriod': {}}):
            with self.subTest(change=change):
                metadata = deepcopy(self.metadata)
                metadata.update(change)
                self.assertIsNone(self.recover(self.raw, metadata, self.date))
        before_validation = datetime(2026, 10, 16, 16, 59, tzinfo=ZoneInfo('America/New_York'))
        self.assertIsNone(self.recover(self.raw, self.metadata, self.date, before_validation))
        self.assertIsNone(self.recover(self.raw.iloc[:-1], self.metadata, self.date))

    def test_rejects_actions_unexplained_adjustment_and_partial_raw_prices(self):
        for column, value, offset in [('Dividends', 1., -1), ('Stock Splits', 2., -1),
                                      ('Capital Gains', 1., -1), ('High', np.nan, -1),
                                      ('Open', 0., -1), ('Adj Close', 1., -2),
                                      ('Close', 100., -1), ('Adj Close', 100., -1)]:
            with self.subTest(column=column, value=value, offset=offset):
                raw = self.raw.copy()
                raw.loc[raw.index[offset], column] = value
                self.assertIsNone(self.recover(raw, self.metadata, self.date))
        for invalid in (0., -1., float('nan'), float('inf')):
            raw = self.raw.copy()
            raw.loc[raw.index[-2], ['Close', 'Adj Close']] = invalid
            self.assertIsNone(self.recover(raw, self.metadata, self.date))


if __name__ == '__main__':
    unittest.main()
