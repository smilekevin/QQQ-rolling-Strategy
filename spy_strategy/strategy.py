"""Causal SPY allocation rules using the existing indicators and opening engine."""
from dataclasses import asdict, dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

import indicators as ta
from execution import run_next_open


TRADE_START = "1995-01-01"
TRAIN_END = "2009-12-31"
DEVELOPMENT_END = "2018-12-31"
HOLDOUT_START = "2019-01-01"


@dataclass(frozen=True)
class Parameters:
    family: str = "multi_indicator"
    sma_len: int = 200
    vol_target: float = 0.16
    max_exposure: float = 1.5
    extension_enabled: bool = True
    extension_threshold: float = 0.10
    extension_release: float = 0.075
    confirm: int = 3
    bear_exit_buffer: float = 0.03
    bull_reentry_buffer: float = 0.01
    lever_volceil: float = 0.35
    recovery_exposure: float = 0.75
    mild_exposure: float = 0.5
    rsi_oversold: int = 25
    oversold_floor: float = 0.15
    deadband: float = 0.15

    def __post_init__(self):
        if self.family not in ("multi_indicator", "trend", "core_trend"):
            raise ValueError("Unknown strategy family")
        if not 1 <= self.max_exposure <= 2 or self.vol_target <= 0:
            raise ValueError("Invalid risk limits")
        if self.sma_len < 2 or self.confirm < 1 or not 0 <= self.deadband < 1:
            raise ValueError("Invalid signal parameters")
        if not 0 <= self.extension_release <= self.extension_threshold:
            raise ValueError("Invalid extension hysteresis")
        if not 0 <= self.mild_exposure <= 1:
            raise ValueError("Core exposure must be between zero and one")


class Strategy:
    def __init__(self, frame):
        self.frame = frame

    @lru_cache(maxsize=32)
    def indicators(self, sma_len, bear_buffer, reentry, rsi, ceiling, upper, lower):
        data = self.frame
        return ta.compute(data.signal_close, data.signal_high, data.signal_low,
                          sma_len=sma_len, bear_exit_buffer=bear_buffer,
                          bull_reentry_buffer=reentry, rsi_oversold=rsi,
                          lever_volceil=ceiling,
                          extension_threshold=upper, extension_release=lower)

    def signals(self, params):
        p = params
        ind = self.indicators(p.sma_len, p.bear_exit_buffer, p.bull_reentry_buffer,
                              p.rsi_oversold, p.lever_volceil,
                              p.extension_threshold, p.extension_release)
        score = (ind.st_bull.astype(int) + (ind.macd_hist > 0).astype(int)
                 + (ind.macd_line > 0).astype(int) + (ind.rsi > 50).astype(int))
        if p.family in ("trend", "core_trend"):
            raw = np.where(ind.macro_bull, np.where(ind.lever_ok, p.max_exposure, 1.), 0.)
        else:
            base = np.where((score >= 3) & ind.lever_ok, p.max_exposure, 1.)
            strong = ind.deep_bear & (ind.macd_line < 0) & ~ind.st_bull
            recovery = ~strong & ind.st_bull & (ind.macd_hist > 0)
            bear = np.where(strong, 0., np.where(recovery, p.recovery_exposure,
                                               p.mild_exposure))
            raw = np.where(ind.macro_bull, base, bear)
        vol = ind.rvol.to_numpy()
        scale = np.ones(len(vol))
        np.divide(p.vol_target, vol, out=scale, where=np.isfinite(vol) & (vol > 0))
        if p.family == "core_trend":
            # A permanent unleveraged SPY core participates in sharp recoveries.
            # Volatility scales only the allocation above that core; it never
            # adds leverage to the core or forces liquidation below the floor.
            raw = np.maximum(raw, p.mild_exposure)
            raw = p.mild_exposure + (raw - p.mild_exposure) * np.minimum(1., scale)
        else:
            raw = raw * np.minimum(1., scale)
        if p.family == "multi_indicator":
            raw = np.where(ind.oversold_latch, np.maximum(raw, p.oversold_floor), raw)
        extension_active = (ind.extension_cap_active.to_numpy() if p.extension_enabled
                            else np.zeros(len(ind), dtype=bool))
        raw = ta.cap_overextension(raw, extension_active)
        raw = np.clip(raw, 0., p.max_exposure)
        rounded = np.round(raw * 20).astype(int)
        confirmed = ta.confirm_exposure(rounded.tolist(), p.confirm,
                                       extension_active.tolist())
        held = confirmed[0]
        targets = []
        for value in confirmed:
            if abs(value - held) >= round(p.deadband * 20):
                held = value
            targets.append(held / 20.)
        signals = pd.Series(targets, index=ind.index, name="target")
        # Warm-up is never an executable allocation or confirmation shortcut.
        signals.loc[ind.sma.isna()] = 0.
        return signals, ind

    def run(self, params, cost_bps=5., delay=1, start=TRADE_START):
        if delay < 1:
            raise ValueError("Signals must execute at least one session later")
        signals, ind = self.signals(params)
        executed = signals.shift(delay).fillna(0.)
        weights = weights_from_exposure(executed).loc[start:]
        equity, exposure, turnover = run_next_open(weights, self.frame, cost_bps / 10000)
        return Result(equity, exposure, turnover, signals, ind, params)


@dataclass
class Result:
    equity: pd.Series
    exposure: pd.Series
    turnover: pd.Series
    signals: pd.Series
    indicators: pd.DataFrame
    params: Parameters | None

    @property
    def returns(self):
        # Include the first trading day's cost and intraday return, starting at 1.
        return self.equity / self.equity.shift(1, fill_value=1.) - 1


def weights_from_exposure(exposure):
    if ((exposure < 0) | (exposure > 2) | ~np.isfinite(exposure)).any():
        raise ValueError("Exposure must be finite and between zero and two")
    q = np.where(exposure <= 1., exposure, 2. - exposure)
    l = np.maximum(0., exposure - 1.)
    return pd.DataFrame({"q": q, "l": l, "c": 1. - q - l}, index=exposure.index)


def benchmark(frame, exposure=1., cost_bps=5.):
    target = pd.Series(exposure, index=frame.index)
    equity, actual, turnover = run_next_open(weights_from_exposure(target).loc[TRADE_START:],
                                            frame, cost_bps / 10000)
    # The 50/50 comparison buys once and drifts, like the existing engine.
    return Result(equity, actual, turnover, target, pd.DataFrame(), None)


def metrics(returns):
    values = returns.to_numpy(dtype=float)
    if not len(values) or not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError("Metrics require finite, solvent daily returns")
    wealth = np.cumprod(1. + values)
    peak = np.maximum.accumulate(np.r_[1., wealth])[1:]
    cagr = float(np.expm1(np.log1p(values).sum() * 252 / len(values)))
    mdd = float(np.min(wealth / peak - 1.))
    volatility = float(values.std(ddof=1) * np.sqrt(252)) if len(values) > 1 else 0.
    return {"cagr": cagr, "total_return": float(wealth[-1] - 1), "mdd": mdd,
            "volatility": volatility,
            "sharpe_rf0": float(values.mean() * 252 / volatility) if volatility else 0.,
            "calmar": cagr / abs(mdd) if mdd < 0 else None,
            "days": len(values), "start": str(returns.index[0].date()),
            "end": str(returns.index[-1].date())}


def period_metrics(result):
    periods = {"full": (TRADE_START, None), "train": (TRADE_START, TRAIN_END),
               "validation": ("2010-01-01", DEVELOPMENT_END),
               "holdout": (HOLDOUT_START, None), "actual_sso": ("2006-06-22", None),
               "since_2010": ("2010-01-01", None), "since_2020": ("2020-01-01", None)}
    return {name: metrics(result.returns.loc[start:end]) for name, (start, end) in periods.items()
            if not result.returns.loc[start:end].empty}


def config_dict(params):
    return asdict(params)
