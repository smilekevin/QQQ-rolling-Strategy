"""Guard R-only increases, unchanged reductions, causality and entrypoint parity."""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import indicators as ta
from test_extension_cap import fixture_prices, load_prefix


class RecoveryConfirmationTests(unittest.TestCase):
    def test_increases_are_fast_but_bullish_restoration_still_confirms(self):
        values = [3, 3, 15, 16, 30, 30, 30]
        recovery = [False, False, True, True, False, False, False]
        self.assertEqual(ta.confirm_exposure(values, 3, recovery_active=recovery),
                         [3, 3, 15, 16, 16, 16, 30])
        # Leaving R cannot resurrect the state from before its fast increase.
        self.assertEqual(ta.confirm_exposure([3, 15, 0, 0, 0], 3,
                                            recovery_active=[False, True, False, False, False]),
                         [3, 15, 15, 15, 0])

    def test_r_reductions_and_other_tiers_keep_three_identical_signatures(self):
        values = [15, 15, 6, 7, 6, 6, 6]
        self.assertEqual(ta.confirm_exposure(values, 3, recovery_active=[True] * 7),
                         [15, 15, 15, 15, 15, 15, 6])
        self.assertEqual(ta.confirm_exposure([3, 15, 15, 15], 3), [3, 3, 3, 15])

    def test_overheat_cap_has_priority_and_state_is_causal(self):
        values = [3, 15, 30, 30, 30, 30]
        active = [False, False, True, False, False, False]
        recovery = [False, True, True, False, False, False]
        expected = [3, 15, 20, 20, 30, 30]
        self.assertEqual(ta.confirm_exposure(values, 3, active, recovery), expected)
        for end in range(1, len(values) + 1):
            self.assertEqual(ta.confirm_exposure(values[:end], 3, active[:end], recovery[:end]),
                             expected[:end])
        self.assertEqual(ta.confirm_exposure([], 3, [], []), [])
        with self.assertRaises(ValueError):
            ta.confirm_exposure([3, 15], 3, recovery_active=[True])

    def test_four_entrypoints_match_with_active_fast_recovery_and_deadband(self):
        data = fixture_prices()
        bt = load_prefix('2_backtest.py', '# 基准', data)
        daily = load_prefix('daily_check.py', 'target=ded[-1]', data)
        opt = load_prefix('opt.py', '\nbase_ind = indicators()', data)
        abl = load_prefix('ablation.py', '\nconfigs = [', data)
        recovery = bt['DEC'].eq('R')
        self.assertTrue(recovery.any())
        old_confirmed = ta.confirm_exposure(bt['sig'].tolist(), 3,
                                            bt['ind'].extension_cap_active.tolist())
        self.assertTrue(np.any(np.asarray(bt['confsig']) > np.asarray(old_confirmed)))
        np.testing.assert_array_equal(daily['recovery'], recovery)
        np.testing.assert_array_equal(daily['res'], bt['confsig'])
        np.testing.assert_allclose(daily['ded'] / 20, bt['e_exec'])
        expected = bt['Wc']
        for weights in [opt['build'](opt['indicators']()), abl['build']()]:
            pd.testing.assert_frame_equal(weights.loc[expected.index], expected,
                                          check_dtype=False)
        # Signals cannot change holdings before the following opening session.
        close_target = pd.Series(bt['e_exec'], index=data.index)
        pd.testing.assert_series_equal(expected.q + 2 * expected.l,
                                       close_target.shift(1).loc[expected.index],
                                       check_names=False)

    def test_fast_r_increase_can_still_be_blocked_by_deadband(self):
        data = fixture_prices()
        signals = ta.compute(data.signal_close, data.signal_high, data.signal_low)
        # Reproduce a 2025-like 0.15 -> 0.25 target: R is true but the
        # ten-point increase is below the unchanged fifteen-point deadband.
        signals['macro_bull'] = False
        signals['deep_bear'] = True
        signals['macd_line'] = -1.
        signals['st_bull'] = False
        signals['macd_hist'] = -1.
        signals['oversold_latch'] = True
        signals['extension_cap_active'] = False
        signals['rvol'] = .60
        signals.loc[signals.index[-5:], ['st_bull', 'macd_hist']] = [True, 1.]
        with patch.object(ta, 'compute', return_value=signals):
            bt = load_prefix('2_backtest.py', '# 基准', data)
            daily = load_prefix('daily_check.py', 'target=ded[-1]', data)
        self.assertEqual(bt['DEC'].iloc[-6], 'F')
        self.assertEqual(bt['DEC'].iloc[-5], 'R')
        self.assertEqual(bt['confsig'][-5:], [5] * 5)
        np.testing.assert_allclose(bt['e_exec'][-5:], [.15] * 5)
        np.testing.assert_allclose(daily['ded'][-5:] / 20, [.15] * 5)


if __name__ == '__main__':
    unittest.main()
