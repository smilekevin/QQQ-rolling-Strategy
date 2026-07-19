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
LEV_CEIL=0.40; RSI_OB=78; CONFIRM=3; DEADBAND=0.10

ap=argparse.ArgumentParser()
ap.add_argument('--current', type=float, default=None, help='你当前的净敞口(如 0.66)')
args=ap.parse_args()

px_ohlc = yf.download('QQQ', start='2022-06-01', progress=False, auto_adjust=True)
px=px_ohlc['Close'].squeeze(); high=px_ohlc['High'].squeeze(); low=px_ohlc['Low'].squeeze()

def ema(s,n): return s.ewm(span=n,adjust=False).mean()
ml=ema(px,12)-ema(px,26); mh=ml-ema(ml,9)
d=px.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
rsi=(100-100/(1+up.ewm(alpha=1/14,adjust=False).mean()/dn.ewm(alpha=1/14,adjust=False).mean().replace(0,np.nan))).fillna(50)
pc=px.shift(1); tr=pd.concat([(high-low),(high-pc).abs(),(low-pc).abs()],axis=1).max(axis=1)
atr=tr.ewm(alpha=1/ST_P,adjust=False).mean(); hl2=(high+low)/2
ub=(hl2+ST_M*atr).values; lb=(hl2-ST_M*atr).values; c=px.values; n=len(px)
fu=ub.copy(); fl=lb.copy(); dr=np.ones(n,int)
for i in range(1,n):
    fu[i]=ub[i] if (ub[i]<fu[i-1] or c[i-1]>fu[i-1]) else fu[i-1]
    fl[i]=lb[i] if (lb[i]>fl[i-1] or c[i-1]<fl[i-1]) else fl[i-1]
    dr[i]=(-1 if c[i]<fl[i-1] else 1) if dr[i-1]==1 else (1 if c[i]>fu[i-1] else -1)
stb=(dr==1)
sma=px.rolling(SMA_LEN).mean(); macro=(px>sma).fillna(False).values
rising=(sma>sma.shift(20)).fillna(False).values
rvol=(px.pct_change().rolling(RVOL_WIN).std()*np.sqrt(252)).values
mlv=ml.values; mhv=mh.values; rsiv=rsi.values

# 逐日目标净敞口
exp=np.empty(n)
for i in range(n):
    if not macro[i]:
        if mlv[i]<0 and not stb[i]: exp[i]=0.0                         # 强空头 -> 现金
        else: exp[i]=max(0.0,min(2.0,0.5*min(VCAP,VOLT/rvol[i])))      # 温和回调:0.5x×波动率目标(V4.3)
        continue
    s=int(stb[i])+(mhv[i]>0)+(mlv[i]>0)+(rsiv[i]>50)
    e=2.0 if s>=4 else (1.5 if s>=3 else 1.0)
    if s>=4 and rsiv[i]>RSI_OB: e=1.5
    if e>1.0 and not (rising[i] and rvol[i]<LEV_CEIL): e=1.0
    e=min(e,MAXE)
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

def tier(e):
    # 敞口分区,边界与 2_backtest.py 的 band() 一致:lo < v <= hi(上界闭)
    if e<=0.25: return 0,'防御'
    if e<=0.75: return 1,'约半仓'
    if e<=1.25: return 2,'约满仓'
    if e<=1.75: return 3,'约1.5倍'
    return 4,'约2倍'
def comp(e):   # 目标敞口 -> 下单比例
    if e<=1.0: return e,0.0,1-e      # QQQ, QLD, cash
    return 2-e, e-1, 0.0
DECNM={'B':'趋势向上','C':'中性偏多','D':'温和回调','E':'强空头/现金'}
def decide_last():                   # 最新决策档(与报告一致)
    i=n-1
    if not macro[i]: return 'E' if (mlv[i]<0 and not stb[i]) else 'D'
    s=int(stb[i])+(mhv[i]>0)+(mlv[i]>0)+(rsiv[i]>50)
    return 'B' if (s>=3 and rising[i] and rvol[i]<LEV_CEIL) else 'C'

q,l,cash=comp(target)
last=px.index[-1].date()
print(f"\n===== V4.3 每日检查 · 基于 {last} 收盘 =====")
print(f"决策档: {DECNM[decide_last()]}   目标净敞口: {target:.2f}x")
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
