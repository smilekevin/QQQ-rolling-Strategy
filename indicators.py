# -*- coding: utf-8 -*-
"""
共享指标模块 —— MACD / RSI / Supertrend / 250日滞回闸门 / 波动率,以及决策档判定。

被 2_backtest.py、daily_check.py 共用,确保"指标 + 决策逻辑"只有一份实现,
避免改一处忘改另一处(见 CLAUDE.md 第 9 节)。opt.py / ablation.py 因需要
扫描不同参数、各自内联了指标,但复用本模块的过热锁存、敞口上限及确认过滤。

约定:所有指标基于 QQQ 收盘价;需要 high/low 计算 Supertrend 的真实 ATR。
"""
import numpy as np, pandas as pd

EXTREME_PANIC_RSI = 25
EXTREME_PANIC_VIX = 30

def extreme_panic(rsi_values, vix_values):
    """观察标记:RSI<=25 且 VIX>=30,不参与策略决策。"""
    return (rsi_values<=EXTREME_PANIC_RSI)&(vix_values>=EXTREME_PANIC_VIX)

def overextension_latch(px, sma, threshold, release_threshold):
    """Arm above the upper SMA extension; release at/below the lower one.

    Evolve on full signal history before rounding/confirmation. A single upper
    crossing arms the raw state; staying in the buffer preserves that state.
    No state is carried through invalid SMA warm-up. Decision tiers are separate.
    """
    if not 0 <= release_threshold <= threshold:
        raise ValueError('Extension thresholds require 0 <= release <= activation')
    active = False
    result = []
    for price, average in zip(px, sma):
        if not np.isfinite(price) or not np.isfinite(average) or average <= 0:
            active = False
        # Compare the price difference to avoid ratio cancellation at exact bounds.
        elif active and price - average <= average * release_threshold:
            active = False
        elif not active and price - average > average * threshold:
            active = True
        result.append(active)
    return pd.Series(result, index=px.index, dtype=bool)

def cap_overextension(exposure, active):
    """Apply the latched 1x cap to raw exposure, before confirmation/deadband.

    Supports scalars/vectors and never raises targets below 1x or blocks exits.
    """
    return np.minimum(exposure, np.where(active, 1.0, np.inf))


def confirm_exposure(vals, k, extension_active=None, recovery_active=None):
    """Confirm rounded 0.05 signatures, with fast overheat cuts and R increases.

    While the overheat latch is active, lower confirmation state to at most
    20 (1x) without waiting k days. Update that state itself so releasing the
    latch cannot resurrect a stale leveraged target. While the decision tier
    is R, a higher raw signature raises confirmation state immediately; lower
    R targets and all other changes still need k identical raw signatures.
    The caller retains the existing deadband and next-open execution.
    """
    if k < 1:
        raise ValueError('Confirmation requires at least one day')
    if extension_active is None:
        extension_active = [False] * len(vals)
    if recovery_active is None:
        recovery_active = [False] * len(vals)
    if len(vals) != len(extension_active) or len(vals) != len(recovery_active):
        raise ValueError('Exposure signatures, extension and recovery state must align')
    if not len(vals):
        return []
    cur = run = vals[0]
    count = 0
    result = []
    for value, active, recovery in zip(vals, extension_active, recovery_active):
        if value == run:
            count += 1
        else:
            run, count = value, 1
        if count >= k:
            cur = run
        if recovery:
            cur = max(cur, value)
        if active:
            cur = min(cur, 20)
        result.append(cur)
    return result

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

def macro_regime(px, sma, bull_reentry_buffer=0.01):
    """多头跌破 SMA 即退出;熊市后需站上 SMA*(1+buffer) 才重新进入多头。"""
    state=None; result=[]
    for price, average in zip(px, sma):
        if np.isnan(average):
            result.append(False)
            continue
        if state is None: state=price>=average
        elif state and price<average: state=False
        elif not state and price>average*(1+bull_reentry_buffer): state=True
        result.append(state)
    return pd.Series(result,index=px.index)

def oversold_latch(macro_bull, sma, rsi_values, threshold=25):
    """熊市 RSI 超跌后锁定底仓状态,直到宏观状态恢复多头。"""
    active=False; result=[]
    for is_bull, average, value in zip(macro_bull, sma, rsi_values):
        if np.isnan(average):
            active=False
        elif is_bull:
            active=False
        elif value<=threshold:
            active=True
        result.append(active)
    return pd.Series(result,index=macro_bull.index)

def compute(px, high, low, sma_len=250, st_period=10, st_mult=3.0,
            rvol_win=20, lever_volceil=0.40, bear_exit_buffer=0.04,
            bull_reentry_buffer=0.01, rsi_oversold=25,
            extension_threshold=0.15, extension_release=0.10):
    """一次性算全套指标,返回 DataFrame:
       macd_line, macd_hist, rsi, st, st_bull, sma, macro_bull, deep_bear,
       oversold_latch, extension_cap_active, sma_rising, lever_ok, rvol"""
    macd_line, macd_hist = macd(px)
    st, st_bull = supertrend(px, high, low, st_period, st_mult)
    rsi_values=rsi(px)
    sma=px.rolling(sma_len).mean()
    macro_bull=macro_regime(px,sma,bull_reentry_buffer)
    deep_bear=(px<sma*(1-bear_exit_buffer)).fillna(False)
    floor_on=oversold_latch(macro_bull,sma,rsi_values,rsi_oversold)
    extension_on=overextension_latch(px,sma,extension_threshold,extension_release)
    sma_rising=(sma>sma.shift(20)).fillna(False)
    rvol=px.pct_change().rolling(rvol_win).std()*np.sqrt(252)
    lever_ok=sma_rising&(rvol<lever_volceil)
    return pd.DataFrame({'macd_line':macd_line,'macd_hist':macd_hist,'rsi':rsi_values,
                         'st':st,'st_bull':st_bull,'sma':sma,'macro_bull':macro_bull,
                         'deep_bear':deep_bear,'oversold_latch':floor_on,
                         'extension_cap_active':extension_on,
                         'sma_rising':sma_rising,'lever_ok':lever_ok,'rvol':rvol})

# ---------------- 决策档(基础/名义仓位)----------------
# 与 2_backtest.targets() 一致:B 仅当动量≥3 且 lever_ok,否则 C;
# 空头区深破缓冲线且 MACD/Supertrend 共振进入 E/F,短期双反转进入 R,其余 D。
DECNAME={'B':'趋势向上','C':'中性偏多','R':'反转恢复','D':'温和回调',
         'F':'超跌底仓','E':'强空头/现金'}

def momentum_score(r):
    """多头区间动量打分 0–4。"""
    return int(r['st_bull'])+int(r['macd_hist']>0)+int(r['macd_line']>0)+int(r['rsi']>50)

def decide_tier(r):
    """返回决策档 'B'/'C'/'R'/'D'/'F'/'E'。r 为 compute() 的一行。"""
    if not r['macro_bull']:
        if r['deep_bear'] and r['macd_line']<0 and not r['st_bull']:
            return 'F' if r['oversold_latch'] else 'E'
        if r['st_bull'] and r['macd_hist']>0:
            return 'R'
        return 'D'
    return 'B' if (momentum_score(r)>=3 and r['lever_ok']) else 'C'
