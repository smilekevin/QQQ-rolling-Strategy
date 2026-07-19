# -*- coding: utf-8 -*-
# 消融实验:在 V4.1 基础上分别去掉 MACD / RSI / Supertrend
import os, pandas as pd, numpy as np
OUT=os.path.dirname(os.path.abspath(__file__))+os.sep
df=pd.read_csv(OUT+'prices.csv',parse_dates=['Date'],index_col='Date')
px=df['qqq']; high=df['qhigh']; low=df['qlow']
rq=df['qqq_ret']; rl=df['qld_ret']; rf=(df['irx']/100.0/252.0)
SMA_LEN=250; VOLT=0.20; VCAP=1.15; CONFIRM=3; COST=5/10000

def ema(s,n): return s.ewm(span=n,adjust=False).mean()
macd_line=ema(px,12)-ema(px,26); macd_hist=macd_line-ema(macd_line,9)
d=px.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
rsi=(100-100/(1+up.ewm(alpha=1/14,adjust=False).mean()/dn.ewm(alpha=1/14,adjust=False).mean().replace(0,np.nan))).fillna(50)
pc=px.shift(1); tr=pd.concat([(high-low),(high-pc).abs(),(low-pc).abs()],axis=1).max(axis=1)
atr=tr.ewm(alpha=1/10,adjust=False).mean(); hl2=(high+low)/2
ub=(hl2+3.0*atr).values; lb=(hl2-3.0*atr).values; c=px.values; n=len(px)
fu=ub.copy(); fl=lb.copy(); direc=np.ones(n,int)
for i in range(1,n):
    fu[i]=ub[i] if (ub[i]<fu[i-1] or c[i-1]>fu[i-1]) else fu[i-1]
    fl[i]=lb[i] if (lb[i]>fl[i-1] or c[i-1]<fl[i-1]) else fl[i-1]
    direc[i]=(-1 if c[i]<fl[i-1] else 1) if direc[i-1]==1 else (1 if c[i]>fu[i-1] else -1)
st_bull=pd.Series(direc==1,index=px.index)
sma=px.rolling(SMA_LEN).mean(); macro=(px>sma).fillna(False)
rising=(sma>sma.shift(20)).fillna(False)
rvol=px.pct_change().rolling(20).std()*np.sqrt(252)
lever_ok=rising&(rvol<0.40)
ind=pd.DataFrame({'ml':macd_line,'mh':macd_hist,'rsi':rsi,'stb':st_bull,
                  'macro':macro,'lok':lever_ok,'rvol':rvol})

def build(use_macd=True,use_rsi=True,use_st=True):
    q=[];l=[];cc=[]
    for _,r in ind.iterrows():
        if not r['macro']:
            # 强空头清仓:用可用指标判断(去掉的指标不参与)
            conds=[]
            if use_macd: conds.append(r['ml']<0)
            if use_st:   conds.append(not r['stb'])
            strong_down = (len(conds)>0 and all(conds))
            w=(0.,0.,1.) if strong_down else (.5,0.,.5)
        else:
            pts=0; mx=0
            if use_st:   mx+=1; pts+=int(r['stb'])
            if use_macd: mx+=2; pts+=int(r['mh']>0)+int(r['ml']>0)
            if use_rsi:  mx+=1; pts+=int(r['rsi']>50)
            if pts>=mx:      state='A'      # 全部看多 -> QLD 全仓
            elif pts>=mx-1:  state='B'      # 差一票   -> QQQ+QLD
            else:            state='C'      # 更弱     -> QQQ 全仓
            if use_rsi and state=='A' and r['rsi']>78: state='B'   # 超买保护
            if state in ('A','B') and not r['lok']: state='C'      # 杠杆熔断
            w={'A':(0.,1.,0.),'B':(.5,.5,0.),'C':(1.,0.,0.)}[state]
            exp=w[0]+2*w[1]
            if r['rvol']>0 and not np.isnan(r['rvol']):
                exp=max(0.,min(2., exp*min(VCAP, VOLT/r['rvol'])))
            w=(exp,0.,1-exp) if exp<=1 else (2-exp,exp-1,0.)
        q.append(w[0]); l.append(w[1]); cc.append(w[2])
    W=pd.DataFrame({'q':q,'l':l,'c':cc},index=ind.index)
    sig=((W['q']+2*W['l'])*20).round().astype(int)
    vals=sig.tolist(); cur=vals[0];run=vals[0];cnt=0;res=[]
    for v in vals:
        if v==run:cnt+=1
        else:run=v;cnt=1
        if cnt>=CONFIRM:cur=run
        res.append(cur)
    lastw={}
    for i,s in zip(W.index,sig): lastw[s]=(W.loc[i,'q'],W.loc[i,'l'],W.loc[i,'c'])
    return pd.DataFrame([lastw[s] for s in res],index=W.index,columns=['q','l','c']).shift(1).bfill()

def run(Wc):
    val=1.;pq=pl=0.;eq=[];ex=[]
    Q=Wc['q'].values;L=Wc['l'].values;C=Wc['c'].values
    RQ=rq.values;RL=rl.values;RF=rf.values
    for i in range(len(Wc)):
        tq,tl,tc=Q[i],L[i],C[i]
        val*=(1-(abs(tq-pq)+abs(tl-pl))*COST); val*=(1+tq*RQ[i]+tl*RL[i]+tc*RF[i])
        eq.append(val); ex.append(tq+2*tl); pq,pl=tq,tl
    return pd.Series(eq,index=Wc.index),pd.Series(ex,index=Wc.index)

def met(e):
    e=e.dropna(); r=e.pct_change().dropna(); yrs=len(e)/252
    cagr=e.iloc[-1]**(1/yrs)-1; vol=r.std()*np.sqrt(252); shp=r.mean()*252/vol
    mdd=(e/e.cummax()-1).min(); cal=cagr/abs(mdd)
    return cagr,mdd,cal,shp,e.iloc[-1]-1
def sub(e,s='2006-06-22'):
    x=e[e.index>=s]; return met(x/x.iloc[0])

configs=[('V4.1 完整(3指标)',dict()),
         ('去掉 MACD',dict(use_macd=False)),
         ('去掉 RSI',dict(use_rsi=False)),
         ('去掉 Supertrend',dict(use_st=False))]
res={}
print(f"{'配置':<20}{'年化':>7}{'总收益':>9}{'最大回撤':>9}{'Calmar':>8}{'夏普':>7}{'平均敞口':>9}")
for name,kw in configs:
    e,ex=run(build(**kw)); cg,md,cal,sh,tot=met(e); res[name]=(cg,md,cal,sh,tot,ex.mean())
    print(f"{name:<20}{cg*100:>6.1f}%{tot*100:>8.0f}%{md*100:>8.1f}%{cal:>8.2f}{sh:>7.2f}{ex.mean():>8.2f}x")
print("\n--- 2006-06 后(全真实 QLD)---")
print(f"{'配置':<20}{'年化':>7}{'最大回撤':>9}{'Calmar':>8}")
for name,kw in configs:
    e,_=run(build(**kw)); cg,md,cal,sh,tot=sub(e)
    print(f"{name:<20}{cg*100:>6.1f}%{md*100:>8.1f}%{cal:>8.2f}")

base=res['V4.1 完整(3指标)']
print("\n相对完整版的变化:")
for name in ['去掉 MACD','去掉 RSI','去掉 Supertrend']:
    cg,md,cal,sh,tot,ae=res[name]
    print(f"  {name:<16} 年化 {(cg-base[0])*100:+.1f}pp  最大回撤 {(md-base[1])*100:+.1f}pp  Calmar {cal-base[2]:+.2f}")
