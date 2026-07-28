# -*- coding: utf-8 -*-
"""共享的 T+1 开盘执行引擎。"""
import pandas as pd


RETURN_COLUMNS = [
    'qqq_overnight_ret', 'qqq_intraday_ret',
    'qld_overnight_ret', 'qld_intraday_ret',
]


def valid_trade_index(df):
    """返回 QQQ/QLD 隔夜和日内收益均有效的真实交易日。"""
    return df.index[df[RETURN_COLUMNS].notna().all(axis=1)]


def run_next_open(weights, df, cost_bps):
    """信号 T 日收盘生成，T+1 开盘调仓；档位内不再平衡。"""
    index = weights.index.intersection(valid_trade_index(df))
    weights = weights.loc[index]
    data = df.loc[index]

    value = 1.0
    qqq_weight = qld_weight = 0.0
    cash_weight = 1.0
    previous_target = None
    equity = []
    exposures = []
    turnovers = []

    for date, target in weights.iterrows():
        qqq_overnight = data.at[date, 'qqq_overnight_ret']
        qld_overnight = data.at[date, 'qld_overnight_ret']
        cash_return = data.at[date, 'irx'] / 100.0 / 252.0

        overnight_factor = (
            qqq_weight * (1 + qqq_overnight)
            + qld_weight * (1 + qld_overnight)
            + cash_weight * (1 + cash_return)
        )
        value *= overnight_factor
        qqq_weight = qqq_weight * (1 + qqq_overnight) / overnight_factor
        qld_weight = qld_weight * (1 + qld_overnight) / overnight_factor
        cash_weight = cash_weight * (1 + cash_return) / overnight_factor

        target_pair = (float(target['q']), float(target['l']))
        turnover = 0.0
        if previous_target is None or target_pair != previous_target:
            turnover = abs(target['q'] - qqq_weight) + abs(target['l'] - qld_weight)
            value *= 1 - turnover * cost_bps
            qqq_weight = float(target['q'])
            qld_weight = float(target['l'])
            cash_weight = float(target['c'])
            previous_target = target_pair

        exposures.append(qqq_weight + 2 * qld_weight)
        turnovers.append(turnover)

        qqq_intraday = data.at[date, 'qqq_intraday_ret']
        qld_intraday = data.at[date, 'qld_intraday_ret']
        intraday_factor = (
            qqq_weight * (1 + qqq_intraday)
            + qld_weight * (1 + qld_intraday)
            + cash_weight
        )
        value *= intraday_factor
        equity.append(value)
        qqq_weight = qqq_weight * (1 + qqq_intraday) / intraday_factor
        qld_weight = qld_weight * (1 + qld_intraday) / intraday_factor
        cash_weight = cash_weight / intraday_factor

    return (
        pd.Series(equity, index=index),
        pd.Series(exposures, index=index),
        pd.Series(turnovers, index=index),
    )
