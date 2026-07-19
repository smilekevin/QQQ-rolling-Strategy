# -*- coding: utf-8 -*-
"""
第 2 步:回测 V4.1 动态滚仓策略  ->  results.json

策略(四档 + 现金,连续杠杆):
  · 宏观闸门:收盘价 vs 250 日均线,定多空大方向。
  · 空头区:  强空头(MACD<0 且 Supertrend 空头)-> 100% 现金(买国债);
             否则温和回调 -> QQQ 半仓(0.5x)+ 半仓现金。
  · 多头区:  动量打分 = Supertrend多头 + MACD柱>0 + MACD线>0 + RSI>50 (0~4)
             -> C=QQQ全仓(1x) / B=QQQ+QLD(1.5x) / A=QLD全仓(2x);RSI>78 时 A 降 B 防吹顶;
             加杠杆(A/B)还需"250日线上行 且 20日波动率<40%"的熔断许可。
  · 波动率目标:最终净敞口 = 档位敞口 × min(VOL_CAP, VOL_TARGET / 20日年化波动率),0~2x 封顶。
  · 抗抖动:  净敞口按 0.05 档、连续 CONFIRM 日确认才切换;信号 T 日生成、T+1 执行(无未来函数)。
  · 现金按 ^IRX 短端国债利率计息;每次调仓计 COST_BPS 单边成本。

运行:  python 2_backtest.py   (需先跑完 1_prepare_data.py 生成 prices.csv)
调参:  只改下面 CONFIG 区。经样本内外验证,SMA_LEN=250 为稳健最优(优于默认 200)。
"""
import os
import pandas as pd, numpy as np, json

# ============================ CONFIG(可调参数)============================
SMA_LEN     = 250     # 趋势闸门均线长度(200/250/300;250 为验证后的稳健选择)
VOL_TARGET  = 0.20    # 目标年化波动率(越低越保守;0.14~0.25 结果不敏感)
VOL_CAP     = 1.15    # 波动目标能放大的杠杆上限倍数(1.0=不放大)
ST_PERIOD   = 10      # Supertrend ATR 周期
ST_MULT     = 3.0     # Supertrend 倍数(2~4)
RVOL_WIN    = 20      # 实际波动率回看窗口(交易日)
LEVER_VOLCEIL = 0.40  # 允许加杠杆的波动率天花板
RSI_OB      = 78      # RSI 超买保护阈值(满分动量但超买时不上满杠杆)
CONFIRM     = 3       # 目标敞口需连续几日确认才切换(降低抖动)
COST_BPS    = 5/10000 # 单边交易成本(5bp)
# ========================================================================

OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep
df = pd.read_csv(OUT+'prices.csv', parse_dates=['Date'], index_col='Date')
px=df['qqq']; high=df['qhigh']; low=df['qlow']
rq=df['qqq_ret']; rl=df['qld_ret']; rf=(df['irx']/100.0/252.0)   # 现金日利率

# ---------------- 指标(全部基于 QQQ)----------------
def ema(s,n): return s.ewm(span=n,adjust=False).mean()
macd_line = ema(px,12)-ema(px,26)
macd_hist = macd_line-ema(macd_line,9)
d=px.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
rsi=(100-100/(1+up.ewm(alpha=1/14,adjust=False).mean()
     /dn.ewm(alpha=1/14,adjust=False).mean().replace(0,np.nan))).fillna(50)
# Supertrend(真实 True Range)
pc=px.shift(1)
tr=pd.concat([(high-low),(high-pc).abs(),(low-pc).abs()],axis=1).max(axis=1)
atr=tr.ewm(alpha=1/ST_PERIOD,adjust=False).mean(); hl2=(high+low)/2
ub=(hl2+ST_MULT*atr).values; lb=(hl2-ST_MULT*atr).values; c=px.values; n=len(px)
fu=ub.copy(); fl=lb.copy(); direc=np.ones(n,int); stv=np.full(n,np.nan)
for i in range(1,n):
    fu[i]=ub[i] if (ub[i]<fu[i-1] or c[i-1]>fu[i-1]) else fu[i-1]
    fl[i]=lb[i] if (lb[i]>fl[i-1] or c[i-1]<fl[i-1]) else fl[i-1]
    direc[i]=(-1 if c[i]<fl[i-1] else 1) if direc[i-1]==1 else (1 if c[i]>fu[i-1] else -1)
    stv[i]=fl[i] if direc[i]==1 else fu[i]
st=pd.Series(stv,index=px.index); st_bull=pd.Series(direc==1,index=px.index)
sma=px.rolling(SMA_LEN).mean(); macro_bull=(px>sma).fillna(False)
sma_rising=(sma>sma.shift(20)).fillna(False)
rvol=px.pct_change().rolling(RVOL_WIN).std()*np.sqrt(252)
lever_ok=sma_rising&(rvol<LEVER_VOLCEIL)
ind=pd.DataFrame({'macd_line':macd_line,'macd_hist':macd_hist,'rsi':rsi,'st_bull':st_bull,'st':st,
                  'macro_bull':macro_bull,'lever_ok':lever_ok,'rvol':rvol})

# ---------------- 目标权重(w_qqq, w_qld, w_cash)----------------
def targets(r):
    if not r['macro_bull']:
        if (r['macd_line']<0) and (not r['st_bull']):
            return (0.0,0.0,1.0)              # 强空头 -> 现金
        return (0.5,0.0,0.5)                   # 温和回调 -> 半仓
    s=int(r['st_bull'])+int(r['macd_hist']>0)+int(r['macd_line']>0)+int(r['rsi']>50)
    state={0:'C',1:'C',2:'C',3:'B',4:'A'}[s]
    if s==4 and r['rsi']>RSI_OB: state='B'
    if state in ('A','B') and not r['lever_ok']: state='C'
    w={'A':(0.0,1.0,0.0),'B':(0.5,0.5,0.0),'C':(1.0,0.0,0.0)}[state]
    exp=w[0]+2*w[1]                             # 波动率目标叠加
    if r['rvol']>0 and not np.isnan(r['rvol']):
        exp=max(0.0,min(2.0, exp*min(VOL_CAP, VOL_TARGET/r['rvol'])))
    return (exp,0.0,1-exp) if exp<=1.0 else (2-exp, exp-1, 0.0)

W=pd.DataFrame([targets(r) for _,r in ind.iterrows()],index=ind.index,columns=['q','l','c'])

# ---------------- 确认过滤 + T+1 执行 ----------------
sig=((W['q']+2*W['l'])*20).round().astype(int)     # 0.05 档的净敞口签名
def confirm(vals,k):
    cur=vals[0]; run=vals[0]; cnt=0; res=[]
    for v in vals:
        if v==run: cnt+=1
        else: run=v; cnt=1
        if cnt>=k: cur=run
        res.append(cur)
    return res
confsig=pd.Series(confirm(sig.tolist(),CONFIRM),index=W.index)
lastw={}
for i,s in zip(W.index,sig): lastw[s]=(W.loc[i,'q'],W.loc[i,'l'],W.loc[i,'c'])
Wc=pd.DataFrame([lastw[s] for s in confsig],index=W.index,columns=['q','l','c']).shift(1).bfill()

# ---------------- 回测引擎(漂移 + 换手成本 + 现金生息)----------------
def run(Wc):
    val=1.0; pq=pl=0.0; eq=[]; exps=[]; turns=[]
    for dt in Wc.index:
        tq,tl,tc=Wc.loc[dt,'q'],Wc.loc[dt,'l'],Wc.loc[dt,'c']
        turn=abs(tq-pq)+abs(tl-pl); val*=(1-turn*COST_BPS)
        val*=(1+tq*rq.loc[dt]+tl*rl.loc[dt]+tc*rf.loc[dt])
        eq.append(val); exps.append(tq+2*tl); turns.append(turn); pq,pl=tq,tl
    return pd.Series(eq,index=Wc.index),pd.Series(exps,index=Wc.index),pd.Series(turns,index=Wc.index)
eq,exp,turn=run(Wc)

# 基准
bh_qqq=(1+rq).cumprod(); bh_qld=(1+rl).cumprod()
st_half=(1+0.5*rq).cumprod(); st_blend=(1+0.5*rq+0.5*rl).cumprod()

def metrics(e):
    e=e.dropna(); r=e.pct_change().dropna(); yrs=len(e)/252
    cagr=e.iloc[-1]**(1/yrs)-1; vol=r.std()*np.sqrt(252); shp=r.mean()*252/vol if vol>0 else 0
    mdd=(e/e.cummax()-1).min(); cal=cagr/abs(mdd) if mdd<0 else np.nan
    yr=e.resample('YE').last().pct_change().dropna()
    return dict(total=e.iloc[-1]-1,cagr=cagr,vol=vol,sharpe=shp,mdd=mdd,calmar=cal,
                best_yr=yr.max(),worst_yr=yr.min())
def rebased(s,start): s2=s[s.index>=start]; return s2/s2.iloc[0]

series={'策略(V4.1动态滚仓)':eq,'QQQ半仓':st_half,'QQQ全仓(=买入持有QQQ)':bh_qqq,
        'QQQ+QLD(50/50)':st_blend,'QLD全仓(=买入持有QLD)':bh_qld}
M ={k:metrics(v)            for k,v in series.items()}
M2={k:metrics(rebased(v,'2006-06-22')) for k,v in series.items()}

print(f"{'方案':<22}{'年化':>7}{'总收益':>9}{'波动':>7}{'夏普':>6}{'回撤':>8}{'Calmar':>7}{'最差年':>7}")
for k,m in M.items():
    print(f"{k:<22}{m['cagr']*100:>6.1f}%{m['total']*100:>8.0f}%{m['vol']*100:>6.1f}%"
          f"{m['sharpe']:>6.2f}{m['mdd']*100:>7.1f}%{m['calmar']:>7.2f}{m['worst_yr']*100:>6.0f}%")
print("--- 2006-06 后(全真实 QLD)---")
for k,m in M2.items():
    print(f"{k:<22}{m['cagr']*100:>6.1f}%  回撤 {m['mdd']*100:6.1f}%  Calmar {m['calmar']:.2f}")

# 敞口分档(用于报告着色/占比)
BANDS=[(-.01,.25,'现金/避险'),(.25,.75,'QQQ半仓'),(.75,1.25,'QQQ全仓'),(1.25,1.75,'QQQ+QLD'),(1.75,2.1,'QLD全仓')]
def band(v):
    for lo,hi,nm in BANDS:
        if lo<v<=hi: return nm
    return 'QLD全仓'
dist=exp.apply(band).value_counts(normalize=True)
nsw=(exp.round(2)!=exp.round(2).shift()).sum()
print(f"\n平均净敞口 {exp.mean():.2f}x  年化换手(单边) {turn.sum()/(len(exp)/252):.2f}  状态切换 {nsw/(len(exp)/252):.1f} 次/年")

# ---------------- 导出 results.json(供报告使用)----------------
def samp(s): return s.resample('W').last().dropna()
export={
 'variant':'V4.1',
 'dates':[d.strftime('%Y-%m-%d') for d in samp(eq).index],
 'equity':{'strategy':samp(eq).round(4).tolist(),'qqq':samp(bh_qqq).round(4).tolist(),
           'qld':samp(bh_qld).round(4).tolist(),'blend':samp(st_blend).round(4).tolist(),'half':samp(st_half).round(4).tolist()},
 'exposure':{'dates':[d.strftime('%Y-%m-%d') for d in samp(exp).index],'vals':samp(exp).round(2).tolist()},
 'state_exp':exp.reindex(samp(eq).index,method='ffill').round(2).tolist(),
 'drawdown':{'strategy':(samp(eq)/samp(eq).cummax()-1).round(4).tolist(),
             'qld':(samp(bh_qld)/samp(bh_qld).cummax()-1).round(4).tolist(),
             'qqq':(samp(bh_qqq)/samp(bh_qqq).cummax()-1).round(4).tolist()},
 'metrics':{k:{kk:(None if isinstance(vv,float) and np.isnan(vv) else round(float(vv),4)) for kk,vv in m.items()} for k,m in M.items()},
 'metrics_sub':{k:{kk:(None if isinstance(vv,float) and np.isnan(vv) else round(float(vv),4)) for kk,vv in m.items()} for k,m in M2.items()},
 'dist':{nm:round(float(dist.get(nm,0)),4) for _,_,nm in BANDS},
 'switches':int(nsw),'ann_switch':round(nsw/(len(exp)/252),1),'ann_turnover':round(float(turn.sum()/(len(exp)/252)),2),
 'avg_exp':round(float(exp.mean()),2),
 'range':[df.index[0].strftime('%Y-%m-%d'),df.index[-1].strftime('%Y-%m-%d')],
 'latest':{'date':df.index[-1].strftime('%Y-%m-%d'),'state':band(exp.iloc[-1]),'exp':round(float(exp.iloc[-1]),2),
           'macd_hist':round(float(macd_hist.iloc[-1]),3),'macd_line':round(float(macd_line.iloc[-1]),3),
           'rsi':round(float(rsi.iloc[-1]),1),'st_bull':bool(st_bull.iloc[-1]),'price':round(float(px.iloc[-1]),2),
           'st_level':round(float(st.iloc[-1]),2),'rvol':round(float(rvol.iloc[-1]),3),'macro_bull':bool(macro_bull.iloc[-1])},
}
json.dump(export,open(OUT+'results.json','w'),ensure_ascii=False)
print(f"\n已保存 {OUT}results.json")
