# -*- coding: utf-8 -*-
"""
第 1 步:下载并准备价格数据  ->  prices.csv

做三件事:
  1) 用 yfinance 下载 QQQ(含高/低价)、QLD、^IRX(13周美债收益率,作杠杆融资成本代理)。
  2) 合成 2006-06(QLD 上市)之前的 QLD:  qld_ret = 2*qqq_ret - (0.95%费率 + 短端利率)/252
     —— 因为 QLD 是 2 倍做多 QQQ 的杠杆 ETF,持有它相当于借 1 倍资金,要付融资成本。
  3) 把"真实 QLD(2006 起)+ 合成 QLD(之前)"拼接成一条完整收益序列,并打印合成质量校验。

输出 prices.csv 列:qqq, qhigh, qlow, qld, qqq_ret, qld_ret, irx
运行:  python 1_prepare_data.py
依赖:  pip install yfinance pandas numpy
"""
import os
import yfinance as yf
import pandas as pd, numpy as np

OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep   # 输出到脚本所在目录
EXPENSE_RATIO = 0.0095    # QLD 年管理费率 0.95%

# ---- 下载 ----
print("下载 QQQ / QLD / ^IRX ...")
qqq_ohlc = yf.download('QQQ', start='1999-01-01', progress=False, auto_adjust=True)
qqq  = qqq_ohlc['Close'].squeeze()
qhigh= qqq_ohlc['High'].squeeze()
qlow = qqq_ohlc['Low'].squeeze()
qld  = yf.download('QLD',  start='2006-01-01', progress=False, auto_adjust=True)['Close'].squeeze()
irx  = yf.download('^IRX', start='1999-01-01', progress=False, auto_adjust=True)['Close'].squeeze()

df = pd.DataFrame({'qqq': qqq, 'qhigh': qhigh, 'qlow': qlow})
df['qld_real'] = qld.reindex(df.index)
df['irx']      = irx.reindex(df.index).ffill().fillna(4.0)   # 百分数
df['qqq_ret']      = df['qqq'].pct_change()
df['qld_real_ret'] = df['qld_real'].pct_change()

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
first = df['qqq_ret'].first_valid_index()
df = df.loc[first:].copy()
df['qld_ret'] = df['qld_ret'].fillna(df['qld_syn_ret'])
df['qqq_ret'] = df['qqq_ret'].fillna(0)
df['qld'] = 100*(1+df['qld_ret'].fillna(0)).cumprod()   # QLD 价格序列(基准化到 100)

df[['qqq','qhigh','qlow','qld','qqq_ret','qld_ret','irx']].to_csv(OUT+'prices.csv')
print(f"已保存 {OUT}prices.csv  共 {len(df)} 行,{df.index[0].date()} ~ {df.index[-1].date()}")
