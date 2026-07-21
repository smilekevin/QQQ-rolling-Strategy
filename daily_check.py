# -*- coding: utf-8 -*-
"""
每日盘后检查:算出 V4.3 策略今日的目标净敞口,并给出"持有/调仓"建议。

用法:
  python daily_check.py                 # 只看今日目标敞口与持仓构成
  python daily_check.py --current 0.66  # 传入你当前的净敞口,输出 持有/调仓 建议
  python daily_check.py --current 1.30  # 例:当前 1.3x

判断规则(与回测一致的执行纪律):
  · 目标跨越档位边界(0.25/0.75/1.25)→ 建议调仓(趋势/风险切换,应及时);
  · 同档内漂移:与当前敞口差 ≥ 0.10x → 调仓,否则持有(忽略零点几的噪声)。
依赖: pip install yfinance pandas numpy
"""
import argparse, numpy as np, pandas as pd, yfinance as yf

# —— 参数须与 2_backtest.py 的 CONFIG 保持一致 ——
SMA_LEN=250; VOLT=0.20; VCAP=1.0; MAXE=1.5; ST_P=10; ST_M=3.0; RVOL_WIN=20
LEV_CEIL=0.40; CONFIRM=3; DEADBAND=0.15

ap=argparse.ArgumentParser()
ap.add_argument('--current', type=float, default=None, help='你当前的净敞口(如 0.66)')
args=ap.parse_args()

px_ohlc = yf.download('QQQ', start='2022-06-01', progress=False, auto_adjust=True)
px=px_ohlc['Close'].squeeze(); high=px_ohlc['High'].squeeze(); low=px_ohlc['Low'].squeeze()

import indicators as ta
ind=ta.compute(px, high, low, sma_len=SMA_LEN, st_period=ST_P, st_mult=ST_M,
               rvol_win=RVOL_WIN, lever_volceil=LEV_CEIL)
n=len(px)
stb=ind['st_bull'].values; macro=ind['macro_bull'].values; rising=ind['sma_rising'].values
rvol=ind['rvol'].values; mlv=ind['macd_line'].values; mhv=ind['macd_hist'].values; rsiv=ind['rsi'].values

# 逐日目标净敞口
exp=np.empty(n)
for i in range(n):
    if not macro[i]:
        if mlv[i]<0 and not stb[i]: exp[i]=0.0                         # 强空头 -> 现金
        else: exp[i]=max(0.0,min(2.0,0.5*min(VCAP,VOLT/rvol[i])))      # 温和回调:0.5x×波动率目标(V4.3)
        continue
    s=int(stb[i])+(mhv[i]>0)+(mlv[i]>0)+(rsiv[i]>50)
    e=MAXE if s>=3 else 1.0
    if e>1.0 and not (rising[i] and rvol[i]<LEV_CEIL): e=1.0
    if rvol[i]>0 and not np.isnan(rvol[i]): e=max(0.0,min(2.0,e*min(VCAP,VOLT/rvol[i])))
    exp[i]=e
# 3 日确认(0.05 档)
sb=np.round(exp*20).astype(int); res=np.empty(n,int); cur=sb[0]; rv=sb[0]; cnt=0
for i in range(n):
    v=sb[i]
    if v==rv: cnt+=1
    else: rv=v; cnt=1
    if cnt>=CONFIRM: cur=rv
    res[i]=cur
conf=res/20.0
target=conf[-1]                      # 今日收盘确认的目标敞口 -> 下个交易日执行

def comp(e):   # 目标敞口 -> 下单比例
    if e<=1.0: return e,0.0,1-e      # QQQ, QLD, cash
    return 2-e, e-1, 0.0
q,l,cash=comp(target)
last=px.index[-1].date()
dec_last=ta.decide_tier(ind.iloc[-1])   # 最新决策档(与回测/报告同一实现)
print(f"\n===== V4.3 每日检查 · 基于 {last} 收盘 =====")
print(f"决策档: {ta.DECNAME[dec_last]}   目标净敞口: {target:.2f}x")
print(f"目标持仓构成: QQQ {q*100:.0f}%   QLD {l*100:.0f}%   现金 {cash*100:.0f}%")
print(f"指标: 价格 {px.iloc[-1]:.1f} | 250日线 {'上方' if macro[-1] else '下方'} | "
      f"Supertrend {'多' if stb[-1] else '空'} | MACD线 {mlv[-1]:+.1f} | RSI {rsiv[-1]:.0f} | 20日波动 {rvol[-1]*100:.0f}%")

if args.current is not None:
    cur_e=args.current; diff=target-cur_e
    # 真正"必调"的经济边界:清仓线(0)与动用杠杆线(1.0)
    def zone(e): return (0 if e<0.05 else (2 if e>1.0+1e-9 else 1))  # 0现金/1无杠杆/2带QLD杠杆
    cross = zone(cur_e)!=zone(target)
    if cross:
        action=f"⚠ 建议调仓:跨越关键边界(现金/无杠杆/带杠杆),调到 {target:.2f}x"
    elif abs(diff)>=DEADBAND:
        action=f"⚠ 建议调仓:偏离 {diff:+.2f}x(≥{DEADBAND}),调到 {target:.2f}x"
    else:
        action=f"✓ 持有不动:与目标仅差 {diff:+.2f}x(<{DEADBAND}),无需交易"
    print(f"\n你当前 {cur_e:.2f}x  ->  {action}")
print()
