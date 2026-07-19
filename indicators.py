# -*- coding: utf-8 -*-
"""
共享指标模块 —— MACD / RSI / Supertrend / 250日闸门 / 波动率,以及决策档判定。

被 2_backtest.py、daily_check.py 共用,确保"指标 + 决策逻辑"只有一份实现,
避免改一处忘改另一处(见 CLAUDE.md 第 9 节)。opt.py / ablation.py 因需要
扫描不同参数、各自内联了指标,不依赖本模块。

约定:所有指标基于 QQQ 收盘价;需要 high/low 计算 Supertrend 的真实 ATR。
"""
import numpy as np, pandas as pd

def ema(s, n): return s.ewm(span=n, adjust=False).mean()

def macd(px):
    """返回 (macd_line, macd_hist),参数 12/26/9。"""
    line = ema(px,12)-ema(px,26)
    hist = line-ema(line,9)
    return line, hist

def rsi(px, period=14):
    """Wilder RSI,缺失填 50。"""
    d=px.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    return (100-100/(1+up.ewm(alpha=1/period,adjust=False).mean()
            /dn.ewm(alpha=1/period,adjust=False).mean().replace(0,np.nan))).fillna(50)

def supertrend(px, high, low, period=10, mult=3.0):
    """返回 (st_line, st_bull)。真实 True Range + Wilder ATR;方向对齐 TradingView 口径。"""
    pc=px.shift(1)
    tr=pd.concat([(high-low),(high-pc).abs(),(low-pc).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/period,adjust=False).mean(); hl2=(high+low)/2
    ub=(hl2+mult*atr).values; lb=(hl2-mult*atr).values; c=px.values; n=len(px)
    fu=ub.copy(); fl=lb.copy(); direc=np.ones(n,int); stv=np.full(n,np.nan)
    for i in range(1,n):
        fu[i]=ub[i] if (ub[i]<fu[i-1] or c[i-1]>fu[i-1]) else fu[i-1]
        fl[i]=lb[i] if (lb[i]>fl[i-1] or c[i-1]<fl[i-1]) else fl[i-1]
        direc[i]=(-1 if c[i]<fl[i-1] else 1) if direc[i-1]==1 else (1 if c[i]>fu[i-1] else -1)
        stv[i]=fl[i] if direc[i]==1 else fu[i]
    return pd.Series(stv,index=px.index), pd.Series(direc==1,index=px.index)

def compute(px, high, low, sma_len=250, st_period=10, st_mult=3.0,
            rvol_win=20, lever_volceil=0.40):
    """一次性算全套指标,返回 DataFrame:
       macd_line, macd_hist, rsi, st, st_bull, macro_bull, sma_rising, lever_ok, rvol"""
    macd_line, macd_hist = macd(px)
    st, st_bull = supertrend(px, high, low, st_period, st_mult)
    sma=px.rolling(sma_len).mean()
    macro_bull=(px>sma).fillna(False)
    sma_rising=(sma>sma.shift(20)).fillna(False)
    rvol=px.pct_change().rolling(rvol_win).std()*np.sqrt(252)
    lever_ok=sma_rising&(rvol<lever_volceil)
    return pd.DataFrame({'macd_line':macd_line,'macd_hist':macd_hist,'rsi':rsi(px),
                         'st':st,'st_bull':st_bull,'macro_bull':macro_bull,
                         'sma_rising':sma_rising,'lever_ok':lever_ok,'rvol':rvol})

# ---------------- 决策档(基础/名义仓位)----------------
# 与 2_backtest.targets() 一致:B 仅当动量≥3 且 lever_ok,否则 C;空头区分 D/E。
DECNAME={'B':'趋势向上','C':'中性偏多','D':'温和回调','E':'强空头/现金'}

def momentum_score(r):
    """多头区间动量打分 0–4。"""
    return int(r['st_bull'])+int(r['macd_hist']>0)+int(r['macd_line']>0)+int(r['rsi']>50)

def decide_tier(r):
    """返回决策档 'B'/'C'/'D'/'E'。r 为 compute() 的一行(或含同名字段的对象)。"""
    if not r['macro_bull']:
        return 'E' if (r['macd_line']<0 and not r['st_bull']) else 'D'
    return 'B' if (momentum_score(r)>=3 and r['lever_ok']) else 'C'
