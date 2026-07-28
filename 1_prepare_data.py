# -*- coding: utf-8 -*-
"""
第 1 步:下载并准备价格数据  ->  prices.csv

做四件事:
  1) 用 yfinance 下载 QQQ(含开/高/低/收)、QLD、^IRX(13周美债收益率,作杠杆融资成本代理)。
  2) 用 QQQ 跟踪的 ^NDX 指数补足上市前历史,只用于 250 日均线等指标暖机;
     回测收益仍从 QQQ 上市后开始,不使用 ^NDX 收益。
  3) 合成 2006-06(QLD 上市)之前的 QLD:  qld_ret = 2*qqq_ret - (0.95%费率 + 短端利率)/252
     —— 因为 QLD 是 2 倍做多 QQQ 的杠杆 ETF,持有它相当于借 1 倍资金,要付融资成本。
  4) 把"真实 QLD(2006 起)+ 合成 QLD(之前)"拼接成完整隔夜/日内收益序列,供 T+1 开盘执行。

输出 prices.csv 列:signal_close/high/low, QQQ/QLD 开收盘价与隔夜/日内收益,irx
运行:  python 1_prepare_data.py
依赖:  pip install yfinance pandas numpy
"""
import os
import yfinance as yf
import pandas as pd, numpy as np

OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep   # 输出到脚本所在目录
EXPENSE_RATIO = 0.0095    # QLD 年管理费率 0.95%
WARMUP_START = '1997-01-01'

# ---- 下载 ----
print("下载 ^NDX / QQQ / QLD / ^IRX ...")
ndx_ohlc = yf.download('^NDX', start=WARMUP_START, progress=False, auto_adjust=True)
qqq_ohlc = yf.download('QQQ', start='1999-01-01', progress=False, auto_adjust=True)
ndx  = ndx_ohlc['Close'].squeeze()
nhigh= ndx_ohlc['High'].squeeze()
nlow = ndx_ohlc['Low'].squeeze()
qqq  = qqq_ohlc['Close'].squeeze()
qopen= qqq_ohlc['Open'].squeeze()
qhigh= qqq_ohlc['High'].squeeze()
qlow = qqq_ohlc['Low'].squeeze()
qld_ohlc = yf.download('QLD', start='2006-01-01', progress=False, auto_adjust=True)
qld_real = qld_ohlc['Close'].squeeze()
qld_open_real = qld_ohlc['Open'].squeeze()
irx  = yf.download('^IRX', start=WARMUP_START, progress=False, auto_adjust=True)['Close'].squeeze()

# ---- 指标暖机序列:^NDX 缩放到 QQQ 上市首日价格,上市后切换为真实 QQQ OHLC ----
qqq_start = qqq.first_valid_index()
anchor = ndx.index[ndx.index.get_indexer([qqq_start], method='pad')[0]]
scale = qqq.loc[qqq_start] / ndx.loc[anchor]
signal_close = (ndx * scale).rename('signal_close')
signal_high = (nhigh * scale).rename('signal_high')
signal_low = (nlow * scale).rename('signal_low')
signal_close.loc[qqq.index] = qqq
signal_high.loc[qhigh.index] = qhigh
signal_low.loc[qlow.index] = qlow

df = pd.DataFrame({'signal_close':signal_close,'signal_high':signal_high,'signal_low':signal_low}).sort_index()
df['qqq'] = qqq.reindex(df.index)
df['qopen'] = qopen.reindex(df.index)
df['qhigh'] = qhigh.reindex(df.index)
df['qlow'] = qlow.reindex(df.index)
df['qld_real'] = qld_real.reindex(df.index)
df['qld_open_real'] = qld_open_real.reindex(df.index)
df['irx']      = irx.reindex(df.index).ffill().fillna(4.0)   # 百分数
df['qqq_ret']      = qqq.pct_change().reindex(df.index)
df['qld_real_ret'] = df['qld_real'].pct_change()
df['qqq_overnight_ret'] = df['qopen'] / df['qqq'].shift(1) - 1
df['qqq_intraday_ret'] = df['qqq'] / df['qopen'] - 1
df['qld_real_overnight_ret'] = df['qld_open_real'] / df['qld_real'].shift(1) - 1
df['qld_real_intraday_ret'] = df['qld_real'] / df['qld_open_real'] - 1

# ---- 合成 QLD 日收益 ----
df['drag']        = (EXPENSE_RATIO + df['irx']/100.0) / 252.0
df['qld_syn_ret'] = 2*df['qqq_ret'] - df['drag']

# ---- 校验:合成 vs 真实(重叠期)----
ov = df.dropna(subset=['qld_real_ret','qld_syn_ret'])
corr = ov['qld_real_ret'].corr(ov['qld_syn_ret'])
yrs  = len(ov)/252
real_cagr = (1+ov['qld_real_ret']).prod()**(1/yrs)-1
syn_cagr  = (1+ov['qld_syn_ret']).prod()**(1/yrs)-1
print(f"合成校验({ov.index[0].date()}~{ov.index[-1].date()}, {yrs:.1f}年):"
      f" 日收益相关性 {corr:.4f}; 真实CAGR {real_cagr*100:.2f}% vs 合成 {syn_cagr*100:.2f}%"
      f" (合成偏乐观 {(syn_cagr-real_cagr)*100:+.2f}%/年)")

# ---- 拼接:有真实用真实,否则用合成 ----
df['qld_ret'] = df['qld_real_ret'].where(df['qld_real_ret'].notna(), df['qld_syn_ret'])
first_trade = df['qqq_ret'].first_valid_index()
df.loc[first_trade:,'qld_ret'] = df.loc[first_trade:,'qld_ret'].fillna(df.loc[first_trade:,'qld_syn_ret'])
df['qld'] = np.nan
df.loc[first_trade:,'qld'] = 100*(1+df.loc[first_trade:,'qld_ret']).cumprod()   # QLD 价格序列(基准化到 100)

# 合成段把 QQQ 隔夜收益放大 2 倍,日内收益反推以严格复原 qld_ret;
# 真实 QLD 上市后直接使用其复权开收盘价。融资与管理费统一计入日内段。
df['qld_syn_overnight_ret'] = 2 * df['qqq_overnight_ret']
df['qld_syn_intraday_ret'] = (
    (1 + df['qld_syn_ret']) / (1 + df['qld_syn_overnight_ret']) - 1
)
real_qld_split = df[['qld_real_ret', 'qld_real_overnight_ret', 'qld_real_intraday_ret']].notna().all(axis=1)
df['qld_overnight_ret'] = df['qld_real_overnight_ret'].where(real_qld_split, df['qld_syn_overnight_ret'])
df['qld_intraday_ret'] = df['qld_real_intraday_ret'].where(real_qld_split, df['qld_syn_intraday_ret'])
df.loc[first_trade:, 'qld_overnight_ret'] = df.loc[first_trade:, 'qld_overnight_ret'].fillna(
    df.loc[first_trade:, 'qld_syn_overnight_ret']
)
df.loc[first_trade:, 'qld_intraday_ret'] = df.loc[first_trade:, 'qld_intraday_ret'].fillna(
    df.loc[first_trade:, 'qld_syn_intraday_ret']
)
df['qld_open'] = df['qld'].shift(1) * (1 + df['qld_overnight_ret'])
df.loc[first_trade, 'qld_open'] = df.loc[first_trade, 'qld'] / (1 + df.loc[first_trade, 'qld_intraday_ret'])

for ticker in ['qqq', 'qld']:
    rebuilt = (1 + df[f'{ticker}_overnight_ret']) * (1 + df[f'{ticker}_intraday_ret']) - 1
    max_error = (rebuilt - df[f'{ticker}_ret']).abs().dropna().max()
    if max_error > 1e-10:
        raise ValueError(f'{ticker.upper()} 隔夜/日内收益无法复原日收益: max_error={max_error}')

cols=['signal_close','signal_high','signal_low','qqq','qopen','qhigh','qlow','qld','qld_open',
      'qqq_ret','qld_ret','qqq_overnight_ret','qqq_intraday_ret',
      'qld_overnight_ret','qld_intraday_ret','irx']
df[cols].to_csv(OUT+'prices.csv')
print(f"指标暖机:使用缩放后的 ^NDX {df.index[0].date()} ~ {qqq_start.date()};回测收益从 {first_trade.date()} 开始")
print(f"已保存 {OUT}prices.csv  共 {len(df)} 行,{df.index[0].date()} ~ {df.index[-1].date()}")
