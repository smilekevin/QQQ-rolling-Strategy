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
    def test_strict_threshold_and_cap_after_volatility_scaling(self):
        self.assertEqual(ta.cap_overextension(1.5, 115., 100., .15), 1.5)
        self.assertEqual(ta.cap_overextension(1.5, 115.01, 100., .15), 1.)
        self.assertEqual(ta.cap_overextension(1.2, 120., 100., .15), 1.)
        # It must not reduce the base to 1x and then multiply by volatility.
        self.assertEqual(ta.cap_overextension(.8, 120., 100., .15), .8)
        self.assertEqual(ta.cap_overextension(0., 120., 100., .15), 0.)
        self.assertEqual(ta.cap_overextension(1.5, 120., np.nan, .15), 1.5)
        np.testing.assert_array_equal(
            ta.cap_overextension(np.array([1.5, 1.2, .75]),
                                 np.array([114., 116., 120.]), 100., .15),
            [1.5, 1., .75])

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
        expected = old_raw.where(extension <= .15, old_raw.clip(upper=1.))
        expected = expected.where(bt['sma'].notna(), old_raw)
        np.testing.assert_allclose(raw, expected)
        self.assertGreater(int(((extension > .15) & (old_raw > 1.)).sum()), 20)
        np.testing.assert_allclose(daily['exp'], raw)
        np.testing.assert_allclose(daily['ded'] / 20., bt['e_exec'])
        expected_weights = bt['Wc']
        for weights in [opt['build'](opt['indicators']()), abl['build']()]:
            pd.testing.assert_frame_equal(weights.loc[expected_weights.index],
                                          expected_weights, check_dtype=False)
        # Both exit and restoration go through the original three-day filter.
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


if __name__ == '__main__':
    unittest.main()
