"""Verify cap semantics and full signal/execution parity across all four entrypoints."""
import ast
from contextlib import ExitStack
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import indicators as ta


ROOT = Path(__file__).resolve().parents[1]


def load_prefix(filename, marker, prices, **overrides):
    tree = ast.parse((ROOT / filename).read_text().split(marker)[0])
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in overrides:
                    node.value = ast.Constant(overrides[target.id])
    ast.fix_missing_locations(tree)
    namespace = {'__file__': str(ROOT / filename)}
    fake_yf = types.ModuleType('yfinance')

    def download(ticker, **kwargs):
        if ticker == '^VIX':
            return pd.DataFrame({'Close': prices.vix})
        return pd.DataFrame({'Close': prices.signal_close,
                             'High': prices.signal_high, 'Low': prices.signal_low})

    fake_yf.download = download
    with ExitStack() as stack:
        stack.enter_context(patch('pandas.read_csv', return_value=prices.copy()))
        stack.enter_context(patch('os.path.exists', return_value=True))
        stack.enter_context(patch.dict(sys.modules, {'yfinance': fake_yf}))
        stack.enter_context(patch.object(sys, 'argv', [filename]))
        exec(compile(tree, str(ROOT / filename), 'exec'), namespace)
    return namespace


def fixture_prices():
    # Include sustained extension, brief crossings, bear exits and recovery.
    returns = np.concatenate([
        np.full(300, .0002), np.full(230, .003), np.full(160, -.004),
        np.full(240, .0025), np.full(170, -.002), np.full(300, .0015),
    ])
    returns += .004 * np.sin(np.arange(len(returns)) * .7)
    close = pd.Series(100 * np.cumprod(1 + returns),
                      index=pd.bdate_range('1997-01-02', periods=len(returns)))
    overnight = pd.Series(.0001, index=close.index)
    daily = close.pct_change()
    qld_daily = 2 * daily - .0001
    frame = pd.DataFrame({
        'signal_close': close, 'signal_high': close * 1.01,
        'signal_low': close * .99, 'qqq_ret': daily, 'qld_ret': qld_daily,
        'qqq_overnight_ret': overnight,
        'qqq_intraday_ret': (1 + daily) / (1 + overnight) - 1,
        'qld_overnight_ret': 2 * overnight,
        'qld_intraday_ret': (1 + qld_daily) / (1 + 2 * overnight) - 1,
        'irx': 4., 'vix': 25.,
    })
    frame.loc[frame.index[:252], ['qqq_overnight_ret', 'qqq_intraday_ret',
                                 'qld_overnight_ret', 'qld_intraday_ret']] = np.nan
    return frame


class ExtensionCapTests(unittest.TestCase):
    def test_strict_thresholds_and_buffer_memory(self):
        px = pd.Series([114., 115., 115.01, 114., 110.01, 110., 114., 116.])
        sma = pd.Series(100., index=px.index)
        state = ta.overextension_latch(px, sma, .15, .10)
        self.assertEqual(state.tolist(), [False, False, True, True, True, False, False, True])
        # The same 14% extension permits leverage before entry and caps it afterward.
        self.assertFalse(state.iloc[0])
        self.assertTrue(state.iloc[3])
        pd.testing.assert_series_equal(
            ta.overextension_latch(px.iloc[:5], sma.iloc[:5], .15, .10), state.iloc[:5])

    def test_warmup_and_rising_average_release(self):
        px = pd.Series([120., 120., 120., 120., 120.])
        sma = pd.Series([np.nan, np.nan, 100., 105., 110.])
        self.assertEqual(ta.overextension_latch(px, sma, .15, .10).tolist(),
                         [False, False, True, True, False])
        with self.assertRaises(ValueError):
            ta.overextension_latch(px, sma, .10, .15)

    def test_cap_after_volatility_scaling_preserves_protective_exits(self):
        self.assertEqual(ta.cap_overextension(1.5, False), 1.5)
        self.assertEqual(ta.cap_overextension(1.5, True), 1.)
        self.assertEqual(ta.cap_overextension(1.2, True), 1.)
        # It must not reduce the base to 1x and then multiply by volatility.
        self.assertEqual(ta.cap_overextension(.8, True), .8)
        self.assertEqual(ta.cap_overextension(.15, True), .15)
        self.assertEqual(ta.cap_overextension(0., True), 0.)
        np.testing.assert_array_equal(
            ta.cap_overextension(np.array([1.5, 1.2, .75]), [False, True, True]),
            [1.5, 1., .75])

    def test_fast_cut_and_confirmed_restoration(self):
        # A single hot close cuts 1.5x to 1x. Even immediate latch release
        # cannot restore the stale 1.5x state before three new signatures.
        values = [30, 30, 20, 30, 30, 30]
        active = [False, False, True, False, False, False]
        self.assertEqual(ta.confirm_exposure(values, 3, active),
                         [30, 30, 20, 20, 20, 30])
        self.assertEqual(ta.confirm_exposure(values[:4], 3, active[:4]),
                         ta.confirm_exposure(values, 3, active)[:4])
        # In the buffer, a separate three-day reduction below 1x still works.
        self.assertEqual(ta.confirm_exposure([30, 30, 10, 10, 10], 3,
                                            [False, False, True, True, True]),
                         [30, 30, 20, 20, 10])
        # The fast cap never increases an already protective allocation.
        self.assertEqual(ta.confirm_exposure([10, 10, 16, 16, 16], 3,
                                            [False, False, True, True, True]),
                         [10, 10, 10, 10, 16])
        self.assertEqual(ta.confirm_exposure([30, 20, 20, 20], 3),
                         [30, 30, 30, 20])
        with self.assertRaises(ValueError):
            ta.confirm_exposure([30, 20], 3, [True])

    def test_full_history_entrypoint_parity_and_confirmation(self):
        data = fixture_prices()
        bt = load_prefix('2_backtest.py', '# 基准', data)
        old = load_prefix('2_backtest.py', '# 基准', data,
                          EXTENSION_THRESHOLD=float('inf'))
        daily = load_prefix('daily_check.py', 'target=ded[-1]', data)
        opt = load_prefix('opt.py', '\nbase_ind = indicators()', data)
        abl = load_prefix('ablation.py', '\nconfigs = [', data)

        old_raw = old['W'].q + 2 * old['W'].l
        raw = bt['W'].q + 2 * bt['W'].l
        extension = data.signal_close / bt['sma'] - 1
        active = False
        reference = []
        for gap in extension:
            if not np.isfinite(gap) or gap <= .10:
                active = False
            elif gap > .15:
                active = True
            reference.append(active)
        expected = old_raw.mask(reference, old_raw.clip(upper=1.))
        np.testing.assert_allclose(raw, expected)
        self.assertTrue(any(reference[i] and .10 < gap <= .15
                            for i, gap in enumerate(extension)))
        self.assertGreater(int(((extension > .15) & (old_raw > 1.)).sum()), 20)
        np.testing.assert_allclose(daily['exp'], raw)
        np.testing.assert_allclose(daily['ded'] / 20., bt['e_exec'])
        expected_weights = bt['Wc']
        for weights in [opt['build'](opt['indicators']()), abl['build']()]:
            pd.testing.assert_frame_equal(weights.loc[expected_weights.index],
                                          expected_weights, check_dtype=False)
        # Other changes retain the original three-day filter without a hot flag.
        self.assertEqual(bt['confirm']([30, 30, 30, 20, 20, 30], 3),
                         [30, 30, 30, 30, 30, 30])
        self.assertEqual(bt['confirm']([30, 20, 20, 20, 30, 30, 30], 3),
                         [30, 30, 30, 20, 20, 20, 30])
        # Next-open execution keeps the full-history signal, then slices trades.
        confirmed = pd.Series(bt['e_exec'], index=data.index)
        pd.testing.assert_series_equal(
            expected_weights.q + 2 * expected_weights.l,
            confirmed.shift(1).loc[expected_weights.index], check_names=False)
        pd.testing.assert_series_equal(bt['DEC'], old['DEC'])
        for namespace, name in [(daily, 'EXTENSION_THRESHOLD'),
                                (opt, 'BASE_EXTENSION_THRESHOLD'),
                                (abl, 'EXTENSION_THRESHOLD')]:
            self.assertEqual(namespace[name], bt['EXTENSION_THRESHOLD'])
        for namespace, name in [(daily, 'EXTENSION_RELEASE'),
                                (opt, 'BASE_EXTENSION_RELEASE'), (abl, 'EXTENSION_RELEASE')]:
            self.assertEqual(namespace[name], bt['EXTENSION_RELEASE'])

    def test_equal_thresholds_reproduce_previous_stateless_raw_cap(self):
        data = fixture_prices()
        previous = load_prefix('2_backtest.py', '# 基准', data, EXTENSION_RELEASE=.15)
        old = load_prefix('2_backtest.py', '# 基准', data,
                          EXTENSION_THRESHOLD=float('inf'))
        old_raw = old['W'].q + 2 * old['W'].l
        gap = data.signal_close / previous['sma'] - 1
        expected = old_raw.mask(gap > .15, old_raw.clip(upper=1.))
        np.testing.assert_allclose(previous['W'].q + 2 * previous['W'].l, expected)


if __name__ == '__main__':
    unittest.main()
