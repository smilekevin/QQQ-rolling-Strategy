"""SPY research contracts: causal data/signals, real SSO boundaries and execution."""
from dataclasses import replace
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from execution import run_next_open
from spy_strategy.data import build_prices, latest_session
from spy_strategy.research import select
from spy_strategy.strategy import Parameters, Strategy, metrics, weights_from_exposure


def prices(index):
    n = len(index)
    close = pd.Series(100 * np.exp(np.arange(n) * .0004 + .02 * np.sin(np.arange(n) / 7)),
                      index=index)
    return pd.DataFrame({"Open": close * .999, "Close": close,
                         "High": close * 1.01, "Low": close * .99})


def execution_frame(index):
    data = prices(index)
    frame = pd.DataFrame({"signal_close": data.Close, "signal_high": data.High,
                          "signal_low": data.Low, "irx": 0.}, index=index)
    for col in ("qqq_overnight_ret", "qqq_intraday_ret", "qld_overnight_ret", "qld_intraday_ret"):
        frame[col] = 0.
    return frame


class SpyDataTests(unittest.TestCase):
    def setUp(self):
        self.spy = prices(pd.bdate_range("1994-12-01", "2006-07-20"))
        self.sso = prices(self.spy.loc["2006-06-21":].index)
        self.irx = self.spy.assign(Close=4.)

    def test_synthetic_segments_compound_exactly_and_real_bars_take_over(self):
        frame = build_prices(self.spy, self.sso, self.irx, "2006-07-20")
        synthetic = frame.synthetic_sso & frame.irx.notna()
        actual = ((1 + frame.qld_overnight_ret) * (1 + frame.qld_intraday_ret) - 1)
        expected = 2 * self.spy.Close.pct_change(fill_method=None) - (.0095 + .04) / 252
        np.testing.assert_allclose(actual[synthetic], expected[synthetic], atol=1e-14)
        first = self.sso.index[1]
        self.assertFalse(frame.loc[first, "synthetic_sso"])
        self.assertAlmostEqual(frame.loc[first, "qld_overnight_ret"],
                               self.sso.Open.iloc[1] / self.sso.Close.iloc[0] - 1)
        self.assertAlmostEqual(frame.loc[first, "qld_intraday_ret"],
                               self.sso.Close.iloc[1] / self.sso.Open.iloc[1] - 1)

    def test_post_inception_gap_is_not_synthesized(self):
        with self.assertRaisesRegex(ValueError, "post-inception"):
            build_prices(self.spy, self.sso.drop(self.sso.index[5]), self.irx, "2006-07-20")

    def test_truncated_sso_history_cannot_turn_real_history_into_synthetic_data(self):
        with self.assertRaisesRegex(ValueError, "inception"):
            build_prices(self.spy, self.sso.iloc[1:], self.irx, "2006-07-20")

    def test_today_yield_cannot_fund_last_night(self):
        self.irx.loc["2006-07-10", "Close"] = 40.
        frame = build_prices(self.spy, self.sso, self.irx, "2006-07-20")
        self.assertEqual(frame.loc["2006-07-10", "irx"], 4.)
        self.assertEqual(frame.loc["2006-07-11", "irx"], 40.)

    def test_intraday_rows_are_excluded_and_stale_etfs_fail(self):
        frame = build_prices(self.spy, self.sso, self.irx, "2006-07-19")
        self.assertEqual(str(frame.index[-1].date()), "2006-07-19")
        with self.assertRaisesRegex(ValueError, "both have"):
            build_prices(self.spy, self.sso.iloc[:-1], self.irx, "2006-07-20")

    def test_completed_nyse_session_respects_holidays_and_publication_delay(self):
        tz = ZoneInfo("America/New_York")
        self.assertEqual(str(latest_session(datetime(2026, 11, 27, 13, 30, tzinfo=tz))), "2026-11-25")
        self.assertEqual(str(latest_session(datetime(2026, 11, 27, 14, 0, tzinfo=tz))), "2026-11-27")
        with self.assertRaisesRegex(ValueError, "timezone"):
            latest_session(datetime(2026, 11, 27))


class SpySignalTests(unittest.TestCase):
    def setUp(self):
        self.frame = execution_frame(pd.bdate_range("1993-01-04", periods=600))

    def test_future_prices_cannot_change_past_signals(self):
        for family in ("multi_indicator", "trend", "core_trend"):
            p = Parameters(family=family, sma_len=150)
            full, _ = Strategy(self.frame).signals(p)
            prefix, _ = Strategy(self.frame.iloc[:400]).signals(p)
            pd.testing.assert_series_equal(full.iloc[:400], prefix)

    def test_close_signal_cannot_trade_that_mornings_open(self):
        self.frame["signal_close"] = 100 * np.exp(np.arange(len(self.frame)) * .001)
        self.frame["signal_high"] = self.frame.signal_close * 1.01
        self.frame["signal_low"] = self.frame.signal_close * .99
        p = Parameters(family="trend", sma_len=20, vol_target=1., confirm=1,
                       extension_enabled=False, deadband=0., lever_volceil=2.)
        normal = Strategy(self.frame).run(p, start="1993-01-01")
        changed = self.frame.copy()
        changed.loc[changed.index[300]:, ["signal_close", "signal_high", "signal_low"]] *= .5
        shock = Strategy(changed).run(p, start="1993-01-01")
        pd.testing.assert_series_equal(normal.exposure.iloc[:301], shock.exposure.iloc[:301])
        self.assertNotEqual(normal.exposure.iloc[301], shock.exposure.iloc[301])
        with self.assertRaises(ValueError):
            Strategy(self.frame).run(p, delay=0)

    def test_targets_have_no_shorting_or_hidden_extra_leverage(self):
        for family in ("multi_indicator", "trend", "core_trend"):
            target, _ = Strategy(self.frame).signals(Parameters(family=family))
            weights = weights_from_exposure(target)
            self.assertTrue((target.between(0., 1.5)).all())
            self.assertTrue((weights >= -1e-12).all().all())
            np.testing.assert_allclose(weights.sum(axis=1), 1.)


class SpyExecutionAndSelectionTests(unittest.TestCase):
    def test_open_purchase_does_not_receive_prior_overnight_gap(self):
        frame = execution_frame(pd.bdate_range("2020-01-01", periods=2))
        frame.iloc[1, frame.columns.get_loc("qqq_overnight_ret")] = .5
        frame.iloc[1, frame.columns.get_loc("qld_overnight_ret")] = 1.
        frame.iloc[1, frame.columns.get_loc("qld_intraday_ret")] = .2
        weights = weights_from_exposure(pd.Series([0., 2.], index=frame.index))
        equity, _, _ = run_next_open(weights, frame, 0.)
        self.assertAlmostEqual(equity.iloc[-1], 1.2)

    def test_unchanged_targets_drift_and_do_not_pay_daily_rebalance_costs(self):
        frame = execution_frame(pd.bdate_range("2020-01-01", periods=2))
        frame.iloc[0, frame.columns.get_loc("qqq_intraday_ret")] = .1
        frame.iloc[0, frame.columns.get_loc("qld_intraday_ret")] = .2
        equity, exposure, turnover = run_next_open(
            weights_from_exposure(pd.Series(1.5, index=frame.index)), frame, .0005)
        self.assertAlmostEqual(equity.iloc[-1], (1 - .0005) * 1.15)
        self.assertEqual(turnover.iloc[1], 0.)
        self.assertGreater(exposure.iloc[1], 1.5)

    def test_first_period_return_and_initial_drawdown_are_counted(self):
        returns = pd.Series([-.1, .1], index=pd.bdate_range("2020-01-01", periods=2))
        m = metrics(returns)
        self.assertAlmostEqual(m["total_return"], -.01)
        self.assertAlmostEqual(m["mdd"], -.1)

    def test_future_holdout_prices_cannot_change_selected_parameters(self):
        dates = (pd.bdate_range("1994-01-03", periods=500)
                 .append(pd.bdate_range("2015-01-02", periods=500))
                 .append(pd.bdate_range("2020-01-02", periods=100)))
        original = execution_frame(dates)
        changed = original.copy()
        changed.loc["2019-01-01":, "signal_close"] *= 10
        configs = [Parameters(sma_len=150), Parameters(sma_len=200)]
        with tempfile.TemporaryDirectory() as temp:
            with patch("spy_strategy.research.candidates", side_effect=lambda phase: iter(configs)):
                first = select(original, Path(temp) / "one")
                second = select(changed, Path(temp) / "two")
        self.assertEqual(first, second)
        self.assertLessEqual(first["data_cutoff"], "2018-12-31")


if __name__ == "__main__":
    unittest.main()
