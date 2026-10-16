# -*- coding: utf-8 -*-
"""
每日盘后检查:算出 V1.8.0 策略今日的目标净敞口,并给出"持有/调仓"建议。

用法:
  python daily_check.py                 # 只看今日目标敞口与持仓构成
  python daily_check.py --current 0.66  # 传入你当前的净敞口,输出 持有/调仓 建议
  python daily_check.py --current 1.30  # 例:当前 1.3x

判断规则(与回测一致的执行纪律):
  · 目标跨越现金/无杠杆/带杠杆边界 → 建议调仓;
  · 同区漂移:与当前敞口差 ≥ 0.15x → 调仓,否则持有。
依赖: pip install yfinance pandas numpy
"""
import argparse, numpy as np, pandas as pd, yfinance as yf

# —— 参数须与 2_backtest.py 的 CONFIG 保持一致 ——
SMA_LEN=250; VOLT=0.20; VCAP=1.0; MAXE=1.5; ST_P=10; ST_M=3.0; RVOL_WIN=20
BEAR_EXIT_BUFFER=0.04; BULL_REENTRY_BUFFER=0.01
RECOVERY_EXPOSURE=0.75; LEV_CEIL=0.40; CONFIRM=3; DEADBAND=0.15
RSI_OVERSOLD=25; OVERSOLD_FLOOR=0.15
EXTENSION_THRESHOLD=0.15
EXTENSION_RELEASE=0.10

ap=argparse.ArgumentParser()
ap.add_argument('--current', type=float, default=None, help='你当前的净敞口(如 0.66)')
args=ap.parse_args()

px_ohlc = yf.download('QQQ', start='2022-06-01', progress=False, auto_adjust=True)
px=px_ohlc['Close'].squeeze(); high=px_ohlc['High'].squeeze(); low=px_ohlc['Low'].squeeze()
vix=yf.download('^VIX', start='2022-06-01', progress=False, auto_adjust=True)['Close'].squeeze().reindex(px.index).ffill()

import indicators as ta
ind=ta.compute(px, high, low, sma_len=SMA_LEN, st_period=ST_P, st_mult=ST_M,
               rvol_win=RVOL_WIN, lever_volceil=LEV_CEIL,
               bear_exit_buffer=BEAR_EXIT_BUFFER, bull_reentry_buffer=BULL_REENTRY_BUFFER,
               rsi_oversold=RSI_OVERSOLD,
               extension_threshold=EXTENSION_THRESHOLD, extension_release=EXTENSION_RELEASE)
n=len(px)
stb=ind['st_bull'].values; macro=ind['macro_bull'].values; deep=ind['deep_bear'].values
floor_on=ind['oversold_latch'].values
rising=ind['sma_rising'].values
rvol=ind['rvol'].values; mlv=ind['macd_line'].values; mhv=ind['macd_hist'].values; rsiv=ind['rsi'].values

# 逐日目标净敞口
exp=np.empty(n)
for i in range(n):
    if not macro[i]:
        if deep[i] and mlv[i]<0 and not stb[i]: exp[i]=0.0             # 深度强空头 -> 默认现金
        else:
            base=RECOVERY_EXPOSURE if stb[i] and mhv[i]>0 else 0.5    # V1.5 反转恢复档 / 温和回调档
            exp[i]=base
            if rvol[i]>0 and not np.isnan(rvol[i]):
                exp[i]=max(0.0,min(2.0,base*min(VCAP,VOLT/rvol[i])))
        if floor_on[i]: exp[i]=max(exp[i],OVERSOLD_FLOOR)              # V1.6 超跌底仓
        continue
    s=int(stb[i])+(mhv[i]>0)+(mlv[i]>0)+(rsiv[i]>50)
    e=MAXE if s>=3 else 1.0
    if e>1.0 and not (rising[i] and rvol[i]<LEV_CEIL): e=1.0
    if rvol[i]>0 and not np.isnan(rvol[i]): e=max(0.0,min(2.0,e*min(VCAP,VOLT/rvol[i])))
    exp[i]=ta.cap_overextension(e,ind['extension_cap_active'].iloc[i])
# 0.05 档:过热降杠杆、R 档加仓免三日确认;其他变化仍确认。
sb=np.round(exp*20).astype(int)
recovery=ind.apply(ta.decide_tier,axis=1).eq('R')
res=np.array(ta.confirm_exposure(sb.tolist(),CONFIRM,ind['extension_cap_active'].tolist(),
                                 recovery_active=recovery.tolist()))
db=int(round(DEADBAND*20)); held=res[0]; ded=np.empty(n,int)
for i,v in enumerate(res):
    if abs(v-held)>=db: held=v
    ded[i]=held
target=ded[-1]/20.0                  # 今日收盘确认+死区后的目标敞口 -> 下个交易日执行

def comp(e):   # 目标敞口 -> 下单比例
    if e<=1.0: return e,0.0,1-e      # QQQ, QLD, cash
    return 2-e, e-1, 0.0
q,l,cash=comp(target)
last=px.index[-1].date()
dec_last=ta.decide_tier(ind.iloc[-1])   # 最新决策档(与回测/报告同一实现)
panic=bool(ta.extreme_panic(rsiv[-1],vix.iloc[-1]))
print(f"\n===== V1.8.0 每日检查 · 基于 {last} 收盘 / 下个交易日开盘执行 =====")
print(f"决策档: {ta.DECNAME[dec_last]}   目标净敞口: {target:.2f}x")
print(f"目标持仓构成: QQQ {q*100:.0f}%   QLD {l*100:.0f}%   现金 {cash*100:.0f}%")
extension=px.iloc[-1]/ind['sma'].iloc[-1]-1
print(f"SMA250 偏离 {extension:+.2%} | 过热限制 {'开启' if ind['extension_cap_active'].iloc[-1] else '关闭'}"
      f"(>{EXTENSION_THRESHOLD:.0%} 开启,≤{EXTENSION_RELEASE:.0%} 解除;带内沿用此前状态;"
      f"过热降杠杆及 R 档加仓不等三日;其他变化仍三日确认;保留死区,下个开盘执行)")
macro_text='多头' if macro[-1] else ('深空头区' if deep[-1] else '回调观察区')
print(f"指标: 价格 {px.iloc[-1]:.1f} | 250日状态 {macro_text} | "
      f"Supertrend {'多' if stb[-1] else '空'} | MACD线 {mlv[-1]:+.1f} | RSI {rsiv[-1]:.0f} | 20日波动 {rvol[-1]*100:.0f}%")
print(f"恐慌观察:VIX {vix.iloc[-1]:.1f} | {'极端恐慌已触发' if panic else '未触发'}(RSI≤{ta.EXTREME_PANIC_RSI} 且 VIX≥{ta.EXTREME_PANIC_VIX},不影响仓位)")

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
