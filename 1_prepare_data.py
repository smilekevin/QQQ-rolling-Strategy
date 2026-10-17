# -*- coding: utf-8 -*-
"""
第 1 步:下载并准备价格数据  ->  prices.csv

做四件事:
  1) 用 yfinance 下载 QQQ(含开/高/低/收)、QLD、^IRX(13周美债收益率)与 ^VIX(恐慌观察标记)。
  2) 用 QQQ 跟踪的 ^NDX 指数补足上市前历史,只用于 250 日均线等指标暖机;
     回测收益仍从 QQQ 上市后开始,不使用 ^NDX 收益。
  3) 合成 2006-06(QLD 上市)之前的 QLD:  qld_ret = 2*qqq_ret - (0.95%费率 + 短端利率)/252
     —— 因为 QLD 是 2 倍做多 QQQ 的杠杆 ETF,持有它相当于借 1 倍资金,要付融资成本。
  4) 把"真实 QLD(2006 起)+ 合成 QLD(之前)"拼接成完整隔夜/日内收益序列,供 T+1 开盘执行。

输出 prices.csv 列:signal_close/high/low, QQQ/QLD 开收盘价与隔夜/日内收益,irx,vix
运行:  python 1_prepare_data.py
依赖:  pip install yfinance pandas numpy
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import yfinance as yf
import pandas as pd, numpy as np

OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep   # 输出到脚本所在目录
EXPENSE_RATIO = 0.0095    # QLD 年管理费率 0.95%
WARMUP_START = '1997-01-01'


def regular_close_bar(raw, metadata, expected_date, now=None):
    """只接受纽约正常收盘时刻的同日报价,用于最新一行缺失的收盘字段。"""
    try:
        if raw.empty or raw.index[-1].date() != expected_date:
            return None
        bar = raw.iloc[-1]
        if pd.notna(bar['Close']) or pd.notna(bar['Adj Close']):
            return None
        tz = ZoneInfo('America/New_York')
        end = metadata['currentTradingPeriod']['regular']['end']
        close_time = datetime.fromtimestamp(end, tz)
        now = now or datetime.now(tz)
        if (metadata['exchangeTimezoneName'] != 'America/New_York'
                or metadata['currency'] != 'USD'
                or close_time.date() != expected_date
                or metadata['regularMarketTime'] != end
                or now.timestamp() < end + 3600):
            return None
        # 遇到当日公司行动时不推断复权因子;上一完整交易日的因子也必须为 1。
        if any(bar.get(name, np.nan) != 0 for name in ('Dividends', 'Stock Splits', 'Capital Gains')):
            return None
        if len(raw) < 2 or not np.isclose(raw.iloc[-2]['Adj Close'], raw.iloc[-2]['Close'],
                                        rtol=1e-7, atol=0):
            return None
        values = {name: float(bar[name]) for name in ('Open', 'High', 'Low')}
        values['Close'] = float(metadata['regularMarketPrice'])
        if not all(np.isfinite(value) and value > 0 for value in values.values()):
            return None
        if not (values['Low'] <= values['Open'] <= values['High']
                and values['Low'] <= values['Close'] <= values['High']):
            return None
        return values
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def download_ohlc(ticker, start):
    frame = yf.download(ticker, start=start, progress=False, auto_adjust=True)
    # 日线 Close/Adj Close 缺失时,auto_adjust 会连开高低也变成 NaN。
    # 同日正常收盘报价可恢复最新一行;不更改历史复权价格或使用盘后价。
    if ticker in ('QQQ', 'QLD') and not frame.empty and frame.iloc[-1][
            frame.columns.get_level_values(0).isin(['Open', 'High', 'Low', 'Close'])].isna().all():
        try:
            quote = yf.Ticker(ticker)
            raw = quote.history(period='5d', auto_adjust=False, actions=True, repair=False)
            metadata = quote.get_history_metadata()
            values = regular_close_bar(raw, metadata, frame.index[-1].date())
            if metadata.get('symbol') == ticker and values is not None:
                for name, value in values.items():
                    frame.loc[frame.index[-1], name] = value
                print(f'{ticker} {frame.index[-1].date()} 使用经时间校验的正常收盘报价 '
                      f'{values["Close"]};仅恢复最新日线')
        except Exception as error:
            print(f'{ticker} 正常收盘报价恢复不可用 ({type(error).__name__});保留完整历史数据')
    # Yahoo 可能先发布成交量,复权 OHLC 仍全空;只裁掉尾部无价格占位行。
    has_price = frame[['Open', 'High', 'Low', 'Close']].notna().any(axis=1)
    if not has_price.any():
        raise ValueError(f'{ticker} 未下载到有效价格')
    last_price_date = frame.index[has_price][-1]
    tail = frame.index > last_price_date
    if tail.any():
        print(f'{ticker} 忽略 {int(tail.sum())} 行尾部空价格占位数据;'
              f'最新价格日期 {last_price_date.date()}')
    frame = frame.loc[:last_price_date]
    for name in ('Open', 'High', 'Low', 'Close'):
        value = frame[name].iloc[-1]
        if not np.all(np.isfinite(value) & (value > 0)):
            raise ValueError(f'{ticker} {last_price_date.date()} 的 {name} 缺失或无效')
    return frame


# ---- 下载 ----
print("下载 ^NDX / QQQ / QLD / ^IRX / ^VIX ...")
ndx_ohlc = download_ohlc('^NDX', WARMUP_START)
qqq_ohlc = download_ohlc('QQQ', '1999-01-01')
qld_ohlc = download_ohlc('QLD', '2006-01-01')
# 任一 ETF 无法恢复时使用共同的完整截止日,避免把上市后缺失的 QLD 合成为收益。
common_end = min(qqq_ohlc.index[-1], qld_ohlc.index[-1])
if qqq_ohlc.index[-1] != qld_ohlc.index[-1]:
    print(f'QQQ/QLD 最新完整日期不一致;共同截止日 {common_end.date()}')
qqq_ohlc = qqq_ohlc.loc[:common_end]
qld_ohlc = qld_ohlc.loc[:common_end]
ndx  = ndx_ohlc['Close'].squeeze()
nhigh= ndx_ohlc['High'].squeeze()
nlow = ndx_ohlc['Low'].squeeze()
qqq  = qqq_ohlc['Close'].squeeze()
qopen= qqq_ohlc['Open'].squeeze()
qhigh= qqq_ohlc['High'].squeeze()
qlow = qqq_ohlc['Low'].squeeze()
qld_real = qld_ohlc['Close'].squeeze()
qld_open_real = qld_ohlc['Open'].squeeze()
irx  = yf.download('^IRX', start=WARMUP_START, progress=False, auto_adjust=True)['Close'].squeeze()
vix  = yf.download('^VIX', start=WARMUP_START, progress=False, auto_adjust=True)['Close'].squeeze()

# ---- 指标暖机序列:^NDX 缩放到 QQQ 上市首日价格,上市后切换为真实 QQQ OHLC ----
qqq_start = qqq.first_valid_index()
anchor = ndx.index[ndx.index.get_indexer([qqq_start], method='pad')[0]]
scale = qqq.loc[qqq_start] / ndx.loc[anchor]
# 上市后只使用 QQQ 的日期和价格,^NDX 不得延长最新信号或填补上市后缺口。
signal_close = pd.concat([ndx.loc[ndx.index < qqq_start] * scale, qqq]).rename('signal_close')
signal_high = pd.concat([nhigh.loc[nhigh.index < qqq_start] * scale, qhigh]).rename('signal_high')
signal_low = pd.concat([nlow.loc[nlow.index < qqq_start] * scale, qlow]).rename('signal_low')

df = pd.DataFrame({'signal_close':signal_close,'signal_high':signal_high,'signal_low':signal_low}).sort_index()
df['qqq'] = qqq.reindex(df.index)
df['qopen'] = qopen.reindex(df.index)
df['qhigh'] = qhigh.reindex(df.index)
df['qlow'] = qlow.reindex(df.index)
df['qld_real'] = qld_real.reindex(df.index)
df['qld_open_real'] = qld_open_real.reindex(df.index)
df['irx']      = irx.reindex(df.index).ffill().fillna(4.0)   # 百分数
df['vix']      = vix.reindex(df.index).ffill()
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
      'qld_overnight_ret','qld_intraday_ret','irx','vix']
df[cols].to_csv(OUT+'prices.csv')
print(f"指标暖机:使用缩放后的 ^NDX {df.index[0].date()} ~ {qqq_start.date()};回测收益从 {first_trade.date()} 开始")
print(f"已保存 {OUT}prices.csv  共 {len(df)} 行,{df.index[0].date()} ~ {df.index[-1].date()}")
