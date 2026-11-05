"""Adjusted SPY/SSO prices, completed NYSE sessions, and explicit synthetic history."""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal


DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output"
SYNTHETIC_FEE = 0.0095
SSO_INCEPTION = pd.Timestamp("2006-06-21")
OHLC = ["Open", "High", "Low", "Close"]


def latest_session(now=None):
    now = now or datetime.now(ZoneInfo("America/New_York"))
    if now.tzinfo is None:
        raise ValueError("An explicit timezone is required")
    day = now.astimezone(ZoneInfo("America/New_York")).date()
    schedule = mcal.get_calendar("NYSE").schedule(day - timedelta(days=14), day)
    ready = schedule[schedule.market_close + pd.Timedelta(hours=1) <= now]
    if ready.empty:
        raise ValueError("No completed NYSE session in the previous 14 days")
    return ready.index[-1].date()


def build_prices(spy, sso, irx, cutoff):
    """Adapt SPY/SSO to the shared execution engine's legacy qqq/qld column names.

    SPY adjusted OHLC includes distributions. SSO adjusted OHLC includes its fees.
    Only pre-inception history (including the first missing overnight split) is
    synthesized; gaps after inception are errors, never synthetic substitutions.
    Yesterday's available Treasury yield funds today's cash/leveraged returns.
    """
    cutoff = pd.Timestamp(cutoff)
    spy = spy.loc[:cutoff, OHLC].copy()
    sso = sso.loc[:cutoff, OHLC].copy()
    if spy.empty or sso.empty or spy.index[-1] != cutoff or sso.index[-1] != cutoff:
        raise ValueError(f"SPY and SSO must both have the completed {cutoff.date()} bar")
    if sso.index[0] != SSO_INCEPTION:
        raise ValueError("SSO history must start at its 2006-06-21 inception; refusing later synthesis")
    for name, frame in (("SPY", spy), ("SSO", sso)):
        values = frame.to_numpy()
        if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
            raise ValueError(f"{name} dates must be unique and sorted")
        if not np.isfinite(values).all() or (values <= 0).any():
            raise ValueError(f"{name} contains missing or invalid OHLC")
        # Adjusted-price multiplication/CSV round trips can differ by one ULP.
        if ((frame.Low > frame[["Open", "Close"]].min(axis=1) * (1 + 1e-10)) |
                (frame.High < frame[["Open", "Close"]].max(axis=1) * (1 - 1e-10))).any():
            raise ValueError(f"{name} OHLC range is invalid")
    aligned = sso.reindex(spy.index)
    if aligned.loc[sso.index[0]:, OHLC].isna().any().any():
        raise ValueError("Missing post-inception SSO bar; refusing synthetic replacement")
    yield_known = irx.Close.reindex(spy.index).ffill().shift(1)
    # No backfill: an unknown initial yield must not come from a future observation.
    frame = pd.DataFrame(index=spy.index)
    frame.index.name = "Date"
    frame["signal_close"] = spy.Close
    frame["signal_high"] = spy.High
    frame["signal_low"] = spy.Low
    frame["spy_open"] = spy.Open
    frame["irx"] = yield_known
    frame["qqq_overnight_ret"] = spy.Open / spy.Close.shift(1) - 1
    frame["qqq_intraday_ret"] = spy.Close / spy.Open - 1
    spy_return = spy.Close.pct_change(fill_method=None)
    synthetic_daily = 2 * spy_return - (SYNTHETIC_FEE + yield_known / 100) / 252
    synthetic_overnight = 2 * frame.qqq_overnight_ret
    synthetic_intraday = (1 + synthetic_daily) / (1 + synthetic_overnight) - 1
    real_overnight = aligned.Open / aligned.Close.shift(1) - 1
    real_intraday = aligned.Close / aligned.Open - 1
    real = real_overnight.notna() & real_intraday.notna()
    frame["qld_overnight_ret"] = real_overnight.where(real, synthetic_overnight)
    frame["qld_intraday_ret"] = real_intraday.where(real, synthetic_intraday)
    frame["synthetic_sso"] = ~real
    valid = frame.loc["1995-01-01":]
    if valid.irx.isna().any() or not np.isfinite(valid.irx).all():
        raise ValueError("Missing previously known Treasury yield")
    for column in ("qqq_overnight_ret", "qqq_intraday_ret",
                   "qld_overnight_ret", "qld_intraday_ret"):
        if not np.isfinite(valid[column]).all() or (valid[column] <= -1).any():
            raise ValueError(f"Invalid executable return: {column}")
    return frame


def load_prices(output=DEFAULT_OUTPUT, refresh=False, as_of=None):
    import yfinance as yf

    output = Path(output)
    raw = output / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    eligible = latest_session()
    cutoff = pd.Timestamp(as_of or eligible).date()
    if cutoff > eligible:
        raise ValueError(f"Latest publishable session is {eligible}; no intraday bars allowed")
    sources, provenance = {}, {}
    for symbol, start in (("SPY", "1993-01-01"), ("SSO", "2006-01-01"),
                          ("^IRX", "1993-01-01"), ("QQQ", "1999-01-01")):
        path = raw / f"{symbol.removeprefix('^')}.csv"
        if refresh or not path.exists():
            data = yf.download(symbol, start=start,
                               end=(cutoff + timedelta(days=1)).isoformat(),
                               auto_adjust=True, progress=False, threads=False)
            if data.empty:
                raise ValueError(f"Yahoo returned no {symbol} data")
            if isinstance(data.columns, pd.MultiIndex):
                data = data.xs(symbol, axis=1, level=-1)
            data.index = pd.to_datetime(data.index).tz_localize(None).normalize()
            data.to_csv(path, index_label="Date")
        data = pd.read_csv(path, index_col="Date", parse_dates=True).loc[:str(cutoff)]
        sources[symbol] = data
        provenance[symbol] = {"raw_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "used_data_sha256": hashlib.sha256(data.to_csv().encode()).hexdigest(),
                              "first": str(data.index[0].date()),
                              "last": str(data.index[-1].date()), "rows": len(data)}
    frame = build_prices(sources["SPY"], sources["SSO"], sources["^IRX"], cutoff)
    expected = mcal.get_calendar("NYSE").valid_days(sources["SPY"].index[0], cutoff).tz_localize(None)
    if len(expected.difference(frame.index)):
        raise ValueError("SPY is missing NYSE sessions; refresh and investigate the source history")
    frame.to_csv(output / "prices.csv")
    metadata = {"provider": "Yahoo Finance / yfinance", "auto_adjust": True,
                "cutoff": str(cutoff), "synthetic_annual_fee": SYNTHETIC_FEE,
                "real_sso_from": str(frame.index[~frame.synthetic_sso][0].date()),
                "sources": provenance}
    (output / "data_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return frame, sources, metadata
