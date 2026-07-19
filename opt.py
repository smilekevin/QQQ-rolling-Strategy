# -*- coding: utf-8 -*-
# Robustness / in-sample vs out-of-sample scan for V4 parameters
import pandas as pd, numpy as np
import os
OUT=os.path.dirname(os.path.abspath(__file__))+os.sep
df=pd.read_csv(OUT+'prices.csv',parse_dates=['Date'],index_col='Date')
px=df['qqq']; high=df['qhigh']; low=df['qlow']
rq=df['qqq_ret']; rl=df['qld_ret']; rf=(df['irx']/100.0/252.0)
def ema(s,n): return s.ewm(span=n,adjust=False).mean()

BASE_SMA=250   # 与主策略 V4.1 一致(此前误用 200,会使 volt/vcap/confirm/lev 扫描在错误闸门下进行)

def indicators(sma_len=BASE_SMA, st_p=10, st_m=3.0, rvol_win=20):
    macd_line=ema(px,12)-ema(px,26); macd_hist=macd_line-ema(macd_line,9)
    d=px.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    rsi=(100-100/(1+up.ewm(alpha=1/14,adjust=False).mean()/dn.ewm(alpha=1/14,adjust=False).mean().replace(0,np.nan))).fillna(50)
    pc=px.shift(1); tr=pd.concat([(high-low),(high-pc).abs(),(low-pc).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/st_p,adjust=False).mean(); hl2=(high+low)/2
    ub=(hl2+st_m*atr).values; lb=(hl2-st_m*atr).values; c=px.values; n=len(px)
    fu=ub.copy(); fl=lb.copy(); direc=np.ones(n,int)
    for i in range(1,n):
        fu[i]=ub[i] if (ub[i]<fu[i-1] or c[i-1]>fu[i-1]) else fu[i-1]
        fl[i]=lb[i] if (lb[i]>fl[i-1] or c[i-1]<fl[i-1]) else fl[i-1]
        direc[i]=(-1 if c[i]<fl[i-1] else 1) if direc[i-1]==1 else (1 if c[i]>fu[i-1] else -1)
    st_bull=pd.Series(direc==1,index=px.index)
    sma=px.rolling(sma_len).mean(); macro=(px>sma).fillna(False)
    rising=(sma>sma.shift(20)).fillna(False)
    rvol=px.pct_change().rolling(rvol_win).std()*np.sqrt(252)
    return pd.DataFrame({'ml':macd_line,'mh':macd_hist,'rsi':rsi,'stb':st_bull,'macro':macro,
                         'rising':rising,'rvol':rvol})

def build(ind, volt=0.20, vcap=1.15, rsi_ob=78, lev_volceil=0.40, confirm_k=3):
    # ---- 全向量化(替代原 iterrows / 逐行 .loc,速度快 ~50x)----
    ml=ind['ml'].values; mh=ind['mh'].values; rsi=ind['rsi'].values
    stb=ind['stb'].values.astype(bool); macro=ind['macro'].values.astype(bool)
    rising=ind['rising'].values.astype(bool); rvol=ind['rvol'].values
    n=len(ind)
    # 多头区:动量打分 -> 基础敞口(C=1 / B=1.5 / A=2)
    s = stb.astype(int)+(mh>0).astype(int)+(ml>0).astype(int)+(rsi>50).astype(int)
    exp = np.where(s>=4, 2.0, np.where(s>=3, 1.5, 1.0))
    exp = np.where((s>=4)&(rsi>rsi_ob), 1.5, exp)          # 超买保护
    lever_ok = rising & (rvol<lev_volceil)
    exp = np.where((exp>1.0)&(~lever_ok), 1.0, exp)        # 杠杆熔断
    # 波动率目标缩放(仅在 rvol 有效处)
    valid = (rvol>0) & (~np.isnan(rvol))
    with np.errstate(divide='ignore',invalid='ignore'):
        scale = np.minimum(vcap, np.where(valid, volt/rvol, vcap))
    exp = np.where(valid, np.clip(exp*scale, 0.0, 2.0), exp)
    # 空头区覆盖:强空头->现金(0),温和回调->半仓(0.5)
    bear = ~macro
    exp = np.where(bear & (ml<0) & (~stb), 0.0, exp)
    exp = np.where(bear & ~((ml<0)&(~stb)), 0.5, exp)
    # 0.05 档确认(单次 O(n) 轻量循环)
    sigb = np.round(exp*20).astype(int)
    res=np.empty(n,int); cur=sigb[0]; run_v=sigb[0]; cnt=0
    for i in range(n):
        v=sigb[i]
        if v==run_v: cnt+=1
        else: run_v=v; cnt=1
        if cnt>=confirm_k: cur=run_v
        res[i]=cur
    e = res/20.0
    e = np.concatenate(([e[0]], e[:-1]))                  # T+1 执行(shift 1, 首值 bfill)
    q = np.where(e<=1.0, e, 2.0-e)
    l = np.where(e<=1.0, 0.0, e-1.0)
    c = 1.0-q-l
    return q,l,c

COST=5/10000
RQ=rq.values; RL=rl.values; RF=rf.values; IDX=rq.index
def run(qlc):
    q,l,c=qlc
    turn = np.abs(np.diff(q,prepend=0.0)) + np.abs(np.diff(l,prepend=0.0))
    ret  = q*RQ + l*RL + c*RF
    eq   = np.cumprod((1-turn*COST)*(1+ret))
    return pd.Series(eq,index=IDX), pd.Series(q+2*l,index=IDX)

def met(e):
    e=e.dropna(); r=e.pct_change().dropna(); yrs=len(e)/252
    cagr=e.iloc[-1]**(1/yrs)-1; vol=r.std()*np.sqrt(252); shp=r.mean()*252/vol if vol>0 else 0
    mdd=(e/e.cummax()-1).min(); cal=cagr/abs(mdd) if mdd<0 else np.nan
    return cagr,mdd,cal,shp
def seg(e,a,b):
    s=e[(e.index>=a)&(e.index<b)]; s=s/s.iloc[0]; return met(s)

TRAIN_END='2013-01-01'  # ~ first 40% for training
base_ind=indicators()

print("="*96)
print(f"A) 波动率目标 volt × 杠杆上限 vcap 网格  —— 指标固定(SMA={BASE_SMA},与主策略一致),只变风控叠加")
print("   每格显示  全周期Calmar / 训练段(≤2012) / 验证段(2013+)   —— 看是否'训练验证都好'")
print("="*96)
volts=[0.14,0.16,0.18,0.20,0.22,0.25]; vcaps=[1.0,1.15,1.3,1.5]
hdr='volt|vcap'
print(f"{hdr:>9}"+"".join(f"{v:>18}" for v in vcaps))
rob={}
for vt in volts:
    row=f"{vt:>9}"
    for vc in vcaps:
        e,_=run(build(base_ind,volt=vt,vcap=vc))
        cf=met(e)[2]; ctr=seg(e,'1999-01-01',TRAIN_END)[2]; cte=seg(e,TRAIN_END,'2027-01-01')[2]
        rob[(vt,vc)]=(cf,ctr,cte,met(e)[0],met(e)[1])
        row+=f"  {cf:4.2f}/{ctr:4.2f}/{cte:4.2f}"
    print(row)

# best by robustness = min(train,test) calmar
best=sorted(rob.items(), key=lambda kv: min(kv[1][1],kv[1][2]), reverse=True)[:5]
print("\n最稳健(训练&验证 Calmar 都高)的前 5 组:")
for (vt,vc),(cf,ctr,cte,cg,md) in best:
    print(f"  volt={vt} vcap={vc:<4} | 全周期 CAGR {cg*100:4.1f}% 回撤 {md*100:5.1f}% Calmar {cf:.2f} | 训练 {ctr:.2f} 验证 {cte:.2f}")

print("\n"+"="*96)
print(f"B) 1D 敏感性(每次只动一个,看是否'高原')  基准 SMA={BASE_SMA} volt=0.20 vcap=1.15")
print("="*96)
def one(label, ind, **kw):
    e,ex=run(build(ind,**kw)); cg,md,cal,sh=met(e)
    print(f"  {label:<26} CAGR {cg*100:5.1f}%  回撤 {md*100:6.1f}%  Calmar {cal:.2f}  夏普 {sh:.2f}  平均敞口 {ex.mean():.2f}x")

print("· SMA 长度:")
for L in [120,150,200,250,300]: one(f"sma_len={L}", indicators(sma_len=L))
print("· Supertrend 倍数:")
for m in [2.0,2.5,3.0,3.5,4.0]: one(f"st_mult={m}", indicators(st_m=m))
print("· 波动率回看窗口:")
for w in [10,15,20,30,40]: one(f"rvol_win={w}", indicators(rvol_win=w))
print("· 确认天数:")
for k in [1,2,3,5,8]: one(f"confirm={k}", base_ind, confirm_k=k)
print("· 加杠杆的波动天花板 lev_volceil:")
for cz in [0.30,0.35,0.40,0.50,0.99]: one(f"lev_volceil={cz}", base_ind, lev_volceil=cz)
