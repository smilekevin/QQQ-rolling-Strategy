"""Compare V1.7.0 confirmation with V1.8.0 on one local price cache.

Run from the repository root: python scripts/research_r_recovery.py
Does not download prices or overwrite results.json / report_data.js.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import indicators as ta
from execution import run_next_open


def weights(namespace, fast, delay=1):
    signatures = namespace['sig'].tolist()
    ind = namespace['ind']
    recovery = namespace['DEC'].eq('R').tolist() if fast else None
    confirmed = ta.confirm_exposure(signatures, namespace['CONFIRM'],
                                    ind.extension_cap_active.tolist(), recovery)
    held = confirmed[0]
    exposures = []
    db = int(round(namespace['DEADBAND'] * 20))
    for value in confirmed:
        if abs(value - held) >= db:
            held = value
        exposures.append(held / 20.)
    exp = np.asarray(exposures)
    q = np.where(exp <= 1, exp, 2 - exp)
    l = np.where(exp <= 1, 0., exp - 1)
    return pd.DataFrame({'q': q, 'l': l, 'c': 1 - q - l},
                        index=ind.index).shift(delay).bfill()


def metrics(equity, start=None, end=None):
    returns = equity.pct_change()
    returns.iloc[0] = equity.iloc[0] - 1
    returns = returns.loc[start:end]
    if returns.empty:
        return None
    values = np.r_[1., (1 + returns).cumprod().to_numpy()]
    cagr = values[-1] ** (252 / len(returns)) - 1
    mdd = (values / np.maximum.accumulate(values) - 1).min()
    return {'cagr': float(cagr), 'mdd': float(mdd),
            'calmar': float(cagr / abs(mdd)) if mdd else None,
            'total': float(values[-1] - 1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT,
                        help='Directory containing prices.csv (default: repository root).')
    data_dir = parser.parse_args().data_dir.resolve()
    # Stop before benchmark construction, printing and the production export.
    # __file__ supplies only the input directory to this non-exporting prefix.
    source = (ROOT / '2_backtest.py').read_text().split('# 基准')[0]
    namespace = {'__file__': str(data_dir / '2_backtest.py')}
    exec(compile(source, str(ROOT / '2_backtest.py'), 'exec'), namespace)
    df = namespace['df']
    cutoff = df.index[-1]
    report = {'data_cutoff': str(cutoff.date()),
              'prices_sha256': hashlib.sha256((data_dir / 'prices.csv').read_bytes()).hexdigest(),
              'metric_convention': 'First daily return included; initial capital included in drawdown.',
              'runs': {}}
    for fast in [False, True]:
        name = 'V1.8.0' if fast else 'V1.7.0'
        for cost, delay in [(namespace['COST_BPS'], 1), (.001, 1), (namespace['COST_BPS'], 2)]:
            target = weights(namespace, fast, delay)
            equity, exposure, turnover = run_next_open(target, df, cost)
            if fast and cost == namespace['COST_BPS'] and delay == 1:
                pd.testing.assert_frame_equal(target.loc[namespace['Wc'].index], namespace['Wc'])
                np.testing.assert_allclose(equity, namespace['eq'])
            key = f'{name}:cost={cost}:delay={delay}'
            report['runs'][key] = {
                'full': metrics(equity), 'since_2006': metrics(equity, '2006-06-22'),
                'since_2010': metrics(equity, '2010-01-01'),
                'since_2020': metrics(equity, '2020-01-01'),
                'recent': metrics(equity, str((cutoff - pd.DateOffset(years=5)).date())),
                'year_2005': metrics(equity, '2005-01-01', '2005-12-31'),
                'year_2025': metrics(equity, '2025-01-01', '2025-12-31'),
                'annual_turnover': float(turnover.sum() / (len(equity) / 252)),
                'annual_rebalances': float((turnover > 1e-12).sum() / (len(equity) / 252)),
                'average_exposure': float(exposure.mean()),
                'blocks': {f'{a}/{b}': metrics(equity, a, b) for a, b in [
                    ('1999-03-11', '2010-12-31'), ('2011-01-01', '2014-12-31'),
                    ('2015-01-01', '2018-12-31'), ('2019-01-01', '2022-12-31'),
                    ('2023-01-01', str(cutoff.date()))]},
            }
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
