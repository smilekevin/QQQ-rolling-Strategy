# -*- coding: utf-8 -*-
"""
第 2 步:回测 V1.6 动态滚仓策略  ->  results.json

策略(六个决策状态,连续杠杆;已去掉 QLD全仓2x 档,最高 1.5x):
  · 宏观闸门:多头跌破 250 日均线即退出;熊市后需站上均线 1% 才恢复多头。
  · 空头区:  低于 250 日线 4% 且 MACD<0、Supertrend 空头 -> 默认 100% 现金;
             RSI<=25 后锁定最低 0.15x 底仓,直到宏观状态恢复多头;
             Supertrend 转多且 MACD 柱转正 -> 反转恢复 0.75x 再套波动率目标;
             否则温和回调 -> 基础 0.5x 再套波动率目标。
  · 多头区:  动量打分 = Supertrend多头 + MACD柱>0 + MACD线>0 + RSI>50 (0~4)
             -> C=QQQ全仓(1x) / 3~4分=QQQ+QLD(1.5x);
             加杠杆还需"250日线上行 且 20日波动率<40%"的熔断许可。
  · 波动率目标:最终净敞口 = 档位敞口 × min(VOL_CAP, VOL_TARGET / 20日年化波动率),默认 0~1.5x。
  · 抗抖动:  净敞口按 0.05 档、连续 CONFIRM 日确认才切换;信号 T 日生成、T+1 执行(无未来函数)。
  · 现金按 ^IRX 短端国债利率计息;每次调仓计 COST_BPS 单边成本。

运行:  python 2_backtest.py   (需先跑完 1_prepare_data.py 生成 prices.csv)
调参:  只改下面 CONFIG 区。经样本内外验证,SMA_LEN=250 为稳健最优(优于默认 200)。
"""
import os
import pandas as pd, numpy as np, json

# ============================ CONFIG(可调参数)============================
SMA_LEN     = 250     # 趋势闸门均线长度(200/250/300;250 为验证后的稳健选择)
BEAR_EXIT_BUFFER = 0.04  # 低于 SMA250 4% 且指标共振才进入 E 现金,过滤浅破震荡
BULL_REENTRY_BUFFER = 0.01 # 熊市后需高于 SMA250 1% 才恢复多头,避免假突破
VOL_TARGET  = 0.20    # 目标年化波动率(越低越保守;0.14~0.25 结果不敏感)
VOL_CAP     = 1.0     # 波动目标只降不升(1.0=不在基础档位上再加杠杆);经验证比 1.15 回撤更低、收益持平
MAX_EXPOSURE= 1.5     # 最高档位上限(1.5=去掉 QLD全仓2x 档;经验证 2x 档不赚风险溢价,砍掉零代价)
RECOVERY_EXPOSURE = 0.75 # V1.5:空头区短期双反转时的基础敞口(0.70~0.80 为稳健区)
RSI_OVERSOLD = 25     # V1.6:熊市 RSI 触发底仓锁定的阈值(23~26 为稳健区)
OVERSOLD_FLOOR = 0.15 # V1.6:触发后最低净敞口,不加杠杆(0.15~0.20 为稳健区)
ST_PERIOD   = 10      # Supertrend ATR 周期
ST_MULT     = 3.0     # Supertrend 倍数(2~4)
RVOL_WIN    = 20      # 实际波动率回看窗口(交易日)
LEVER_VOLCEIL = 0.40  # 允许加杠杆的波动率天花板
CONFIRM     = 3       # 目标敞口需连续几日确认才切换(降低抖动)
DEADBAND    = 0.15    # 死区:确认目标与"当前持有敞口"偏离≥此值才调仓,否则沿用前一日(0=不设死区;0.05~0.25 为高原,0.15 换手更低)
COST_BPS    = 5/10000 # 单边交易成本(5bp)
# ========================================================================

OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep
df = pd.read_csv(OUT+'prices.csv', parse_dates=['Date'], index_col='Date')
px=df['signal_close']; high=df['signal_high']; low=df['signal_low']
rq=df['qqq_ret']; rl=df['qld_ret']; rf=(df['irx']/100.0/252.0)   # 现金日利率

# ---------------- 指标 + 决策档(共享模块,见 indicators.py)----------------
import indicators as ta
ind=ta.compute(px, high, low, sma_len=SMA_LEN, st_period=ST_PERIOD, st_mult=ST_MULT,
               rvol_win=RVOL_WIN, lever_volceil=LEVER_VOLCEIL,
               bear_exit_buffer=BEAR_EXIT_BUFFER, bull_reentry_buffer=BULL_REENTRY_BUFFER,
               rsi_oversold=RSI_OVERSOLD)
macd_line=ind['macd_line']; macd_hist=ind['macd_hist']; rsi=ind['rsi']
st=ind['st']; st_bull=ind['st_bull']; sma=ind['sma']; macro_bull=ind['macro_bull']
deep_bear=ind['deep_bear']; floor_on=ind['oversold_latch']; rvol=ind['rvol']
DECNAME=ta.DECNAME
DEC=ind.apply(ta.decide_tier,axis=1)   # 决策档(基础仓位,着色/占比用)
DEC_exec=DEC.shift(1).bfill()          # T+1,与执行时间线对齐

# ---------------- 目标权重(w_qqq, w_qld, w_cash)----------------
def targets(r):
    if not r['macro_bull']:
        if r['deep_bear'] and (r['macd_line']<0) and (not r['st_bull']):
            e=0.0                                      # 强空头默认现金
        else:
            # V1.5:空头区出现 Supertrend + MACD柱双反转时分阶段恢复,否则维持 D 档。
            base=RECOVERY_EXPOSURE if r['st_bull'] and r['macd_hist']>0 else 0.5
            e=base
            if r['rvol']>0 and not np.isnan(r['rvol']):
                e=max(0.0,min(2.0, base*min(VOL_CAP, VOL_TARGET/r['rvol'])))
        if r['oversold_latch']:
            e=max(e,OVERSOLD_FLOOR)                    # V1.6:超跌后保留无杠杆底仓
        return (e,0.0,1-e)
    s=int(r['st_bull'])+int(r['macd_hist']>0)+int(r['macd_line']>0)+int(r['rsi']>50)
    exp=MAX_EXPOSURE if s>=3 else 1.0
    if exp>1.0 and not r['lever_ok']:
        exp=1.0
    if r['rvol']>0 and not np.isnan(r['rvol']): # 波动率目标叠加
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
confsig=confirm(sig.tolist(),CONFIRM)              # 0.05 档、经确认的目标净敞口(单位=0.05)
# 死区:仅当确认目标与"当前持有档"偏离 ≥ DEADBAND 才调仓,否则沿用前一日敞口
DB=int(round(DEADBAND*20)); held=confsig[0]; ded=[]
for v in confsig:
    if abs(v-held)>=DB: held=v
    ded.append(held)
e_exec=np.array(ded)/20.0                           # 实际执行的目标净敞口
q=np.where(e_exec<=1,e_exec,2-e_exec); l=np.where(e_exec<=1,0.0,e_exec-1.0); cash=1.0-q-l
Wc=pd.DataFrame({'q':q,'l':l,'c':cash},index=W.index).shift(1).bfill()

# ^NDX 仅用于 QQQ 上市前的指标暖机;收益、换手和全部绩效从真实 QQQ 日收益开始。
trade_index=df.index[df['qqq_ret'].notna() & df['qld_ret'].notna()]
Wc=Wc.loc[trade_index]
rq=rq.loc[trade_index]; rl=rl.loc[trade_index]; rf=rf.loc[trade_index]

# ---------------- 回测引擎(档位内不再平衡,仅换档时调仓 + 现金生息)----------------
# 持有期内任凭 QQQ/QLD 权重随行情漂移(不做日内再平衡),只有当目标档位变化时
# 才从当前(漂移后)权重成交到新目标,并按实际成交量计交易成本 —— 与实盘一致。
def run(Wc):
    val=1.0; wq=wl=wc=0.0; ptq=ptl=None; eq=[]; exps=[]; turns=[]
    Q=Wc['q'].values; L=Wc['l'].values; C=Wc['c'].values
    RQ=rq.values; RL=rl.values; RF=rf.values
    for i in range(len(Wc)):
        tq,tl,tc=Q[i],L[i],C[i]
        turn=0.0
        if ptq is None or abs(tq-ptq)>1e-9 or abs(tl-ptl)>1e-9:   # 目标档位变化才调仓
            turn=abs(tq-wq)+abs(tl-wl); val*=(1-turn*COST_BPS)
            wq,wl,wc=tq,tl,tc; ptq,ptl=tq,tl
        val*=(1+wq*RQ[i]+wl*RL[i]+wc*RF[i])
        eq.append(val); exps.append(wq+2*wl); turns.append(turn)
        nq=wq*(1+RQ[i]); nl=wl*(1+RL[i]); ncash=wc*(1+RF[i]); tot=nq+nl+ncash  # 漂移到次日
        if tot>0: wq,wl,wc=nq/tot,nl/tot,ncash/tot
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

series={'策略(V1.6超跌底仓)':eq,'QQQ半仓':st_half,'QQQ全仓(=买入持有QQQ)':bh_qqq,
        'QQQ+QLD(50/50)':st_blend,'QLD全仓(=买入持有QLD)':bh_qld}
M ={k:metrics(v)            for k,v in series.items()}
M2={k:metrics(rebased(v,'2006-06-22')) for k,v in series.items()}
M2010={k:metrics(rebased(v,'2010-01-01')) for k,v in series.items()}
M2020={k:metrics(rebased(v,'2020-01-01')) for k,v in series.items()}

print(f"{'方案':<22}{'年化':>7}{'总收益':>9}{'波动':>7}{'夏普':>6}{'回撤':>8}{'Calmar':>7}{'最差年':>7}")
for k,m in M.items():
    print(f"{k:<22}{m['cagr']*100:>6.1f}%{m['total']*100:>8.0f}%{m['vol']*100:>6.1f}%"
          f"{m['sharpe']:>6.2f}{m['mdd']*100:>7.1f}%{m['calmar']:>7.2f}{m['worst_yr']*100:>6.0f}%")
print("--- 2006-06 后(全真实 QLD)---")
for k,m in M2.items():
    print(f"{k:<22}{m['cagr']*100:>6.1f}%  回撤 {m['mdd']*100:6.1f}%  Calmar {m['calmar']:.2f}")

dist=DEC_exec.reindex(eq.index).map(DECNAME).value_counts(normalize=True)     # 各决策档时间占比
tgt_exp=(Wc['q']+2*Wc['l']).round(2)          # 目标敞口(换档信号),用于统计切换次数
nsw=(tgt_exp!=tgt_exp.shift()).sum()

# 最近一次调仓:用执行后的目标敞口序列(0.05档+死区)找最后一次变化
exec_ser=pd.Series(e_exec,index=W.index).round(2)
_chg=exec_ser.ne(exec_ser.shift()); _chg.iloc[0]=False
_ci=np.where(_chg.values)[0]
if len(_ci): last_reb=exec_ser.index[_ci[-1]]; prev_e=float(exec_ser.iloc[_ci[-1]-1])
else:        last_reb=exec_ser.index[0];        prev_e=float(exec_ser.iloc[0])
cur_e=float(exec_ser.iloc[-1]); days_since=int((df.index[-1]-last_reb).days)
print(f"\n平均净敞口 {exp.mean():.2f}x  年化换手(单边) {turn.sum()/(len(exp)/252):.2f}  状态切换 {nsw/(len(exp)/252):.1f} 次/年")

# ---------------- 导出 results.json(供报告使用)----------------
def samp(s): return s.dropna()          # 日线(每个交易日一个点),支持按日缩放
export={
 'variant':'V1.6',
 'dates':[d.strftime('%Y-%m-%d') for d in samp(eq).index],
 'equity':{'strategy':samp(eq).round(3).tolist(),'qqq':samp(bh_qqq).round(3).tolist(),
           'qld':samp(bh_qld).round(3).tolist(),'blend':samp(st_blend).round(3).tolist(),'half':samp(st_half).round(3).tolist()},
 'state_exp':samp(exp).round(2).tolist(),                            # 每日净敞口(敞口图+悬浮共用;回撤在前端由 equity 算)
 'decision':DEC_exec.reindex(samp(eq).index,method='ffill').tolist(),   # 每日决策档(B/C/R/D/F/E),着色用
 'metrics':{k:{kk:(None if isinstance(vv,float) and np.isnan(vv) else round(float(vv),4)) for kk,vv in m.items()} for k,m in M.items()},
 'metrics_sub':{k:{kk:(None if isinstance(vv,float) and np.isnan(vv) else round(float(vv),4)) for kk,vv in m.items()} for k,m in M2.items()},
 'metrics_2010':{k:{kk:(None if isinstance(vv,float) and np.isnan(vv) else round(float(vv),4)) for kk,vv in m.items()} for k,m in M2010.items()},
 'metrics_2020':{k:{kk:(None if isinstance(vv,float) and np.isnan(vv) else round(float(vv),4)) for kk,vv in m.items()} for k,m in M2020.items()},
 'dist':{DECNAME[k]:round(float(dist.get(DECNAME[k],0)),4) for k in ['B','C','R','D','F','E']},
 'switches':int(nsw),'ann_switch':round(nsw/(len(exp)/252),1),'ann_turnover':round(float(turn.sum()/(len(exp)/252)),2),
 'avg_exp':round(float(exp.mean()),2),
 'range':[eq.index[0].strftime('%Y-%m-%d'),eq.index[-1].strftime('%Y-%m-%d')],
 'latest':{'date':df.index[-1].strftime('%Y-%m-%d'),'state':DECNAME[DEC.iloc[-1]],'dec':DEC.iloc[-1],'exp':round(cur_e,2),
           'last_reb':last_reb.strftime('%Y-%m-%d'),'days_since':days_since,
           'prev_exp':round(prev_e,2),
           'macd_hist':round(float(macd_hist.iloc[-1]),3),'macd_line':round(float(macd_line.iloc[-1]),3),
           'rsi':round(float(rsi.iloc[-1]),1),'st_bull':bool(st_bull.iloc[-1]),'price':round(float(px.iloc[-1]),2),
           'st_level':round(float(st.iloc[-1]),2),'rvol':round(float(rvol.iloc[-1]),3),
           'sma250':round(float(sma.iloc[-1]),2),'macro_bull':bool(macro_bull.iloc[-1]),
           'deep_bear':bool(deep_bear.iloc[-1]),'oversold_latch':bool(floor_on.iloc[-1])},
}
json.dump(export,open(OUT+'results.json','w'),ensure_ascii=False)
print(f"\n已保存 {OUT}results.json")
