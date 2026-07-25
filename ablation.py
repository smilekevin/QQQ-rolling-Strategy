# -*- coding: utf-8 -*-
# V1.6 消融实验:在当前策略口径下分别去掉 MACD / RSI / Supertrend。
#
# 默认逻辑与 2_backtest.py V1.6 对齐:4%/1% 宏观滞回、VOL_CAP=1.0、
# MAX_EXPOSURE=1.5、R=0.75x / D=0.5x * 波动率目标、RSI<=25 后 0.15x 底仓、
# 0.15x 死区、T+1、不再平衡。
import os
import sys
import pandas as pd
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep
DATA = OUT + 'prices.csv'
if not os.path.exists(DATA):
    sys.exit('缺少 prices.csv: 请先运行 python 1_prepare_data.py')

df = pd.read_csv(DATA, parse_dates=['Date'], index_col='Date')
px = df['signal_close']; high = df['signal_high']; low = df['signal_low']
rq = df['qqq_ret']; rl = df['qld_ret']; rf = df['irx'] / 100.0 / 252.0
TRADE_INDEX = df.index[df['qqq_ret'].notna() & df['qld_ret'].notna()]

SMA_LEN = 250
BEAR_EXIT_BUFFER = 0.04
BULL_REENTRY_BUFFER = 0.01
VOLT = 0.20
VCAP = 1.0
MAX_EXPOSURE = 1.5
RECOVERY_EXPOSURE = 0.75
RSI_OVERSOLD = 25
OVERSOLD_FLOOR = 0.15
LEV_VOLCEIL = 0.40
CONFIRM = 3
DEADBAND = 0.15
COST = 5 / 10000


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


macd_line = ema(px, 12) - ema(px, 26)
macd_hist = macd_line - ema(macd_line, 9)
d = px.diff()
up = d.clip(lower=0)
dn = -d.clip(upper=0)
rsi = (100 - 100 / (1 + up.ewm(alpha=1/14, adjust=False).mean()
       / dn.ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan))).fillna(50)

pc = px.shift(1)
tr = pd.concat([(high-low), (high-pc).abs(), (low-pc).abs()], axis=1).max(axis=1)
atr = tr.ewm(alpha=1/10, adjust=False).mean()
hl2 = (high + low) / 2
ub = (hl2 + 3.0 * atr).values
lb = (hl2 - 3.0 * atr).values
c = px.values
n = len(px)
fu = ub.copy()
fl = lb.copy()
direc = np.ones(n, int)
for i in range(1, n):
    fu[i] = ub[i] if (ub[i] < fu[i-1] or c[i-1] > fu[i-1]) else fu[i-1]
    fl[i] = lb[i] if (lb[i] > fl[i-1] or c[i-1] < fl[i-1]) else fl[i-1]
    direc[i] = (-1 if c[i] < fl[i-1] else 1) if direc[i-1] == 1 else (1 if c[i] > fu[i-1] else -1)

st_bull = pd.Series(direc == 1, index=px.index)
sma = px.rolling(SMA_LEN).mean()
macro_values = []
macro_state = None
for price, average in zip(px, sma):
    if np.isnan(average):
        macro_values.append(False)
        continue
    if macro_state is None: macro_state = price >= average
    elif macro_state and price < average: macro_state = False
    elif not macro_state and price > average * (1 + BULL_REENTRY_BUFFER): macro_state = True
    macro_values.append(macro_state)
macro = pd.Series(macro_values, index=px.index)
deep_bear = (px < sma * (1 - BEAR_EXIT_BUFFER)).fillna(False)
rising = (sma > sma.shift(20)).fillna(False)
rvol = px.pct_change().rolling(20).std() * np.sqrt(252)
lever_ok = rising & (rvol < LEV_VOLCEIL)
ind = pd.DataFrame({
    'ml': macd_line, 'mh': macd_hist, 'rsi': rsi, 'stb': st_bull,
    'macro': macro, 'deep': deep_bear, 'sma': sma, 'lok': lever_ok, 'rvol': rvol
})


def confirm(vals, k):
    cur = vals[0]
    run = vals[0]
    cnt = 0
    res = []
    for v in vals:
        if v == run:
            cnt += 1
        else:
            run = v
            cnt = 1
        if cnt >= k:
            cur = run
        res.append(cur)
    return np.array(res)


def build(use_macd=True, use_rsi=True, use_st=True):
    exp = []
    floor_active = False
    for _, r in ind.iterrows():
        valid = r['rvol'] > 0 and not np.isnan(r['rvol'])
        scale = min(VCAP, VOLT / r['rvol']) if valid else VCAP

        if np.isnan(r['sma']) or r['macro']:
            floor_active = False
        elif use_rsi and r['rsi'] <= RSI_OVERSOLD:
            floor_active = True

        if not r['macro']:
            down_conds = []
            if use_macd:
                down_conds.append(r['ml'] < 0)
            if use_st:
                down_conds.append(not r['stb'])
            strong_down = bool(r['deep']) and len(down_conds) > 0 and all(down_conds)
            recovery_conds = []
            if use_macd:
                recovery_conds.append(r['mh'] > 0)
            if use_st:
                recovery_conds.append(r['stb'])
            recovery = len(recovery_conds) > 0 and all(recovery_conds)
            base = RECOVERY_EXPOSURE if recovery else 0.5
            e = 0.0 if strong_down else max(0.0, min(2.0, base * scale))
            if floor_active:
                e = max(e, OVERSOLD_FLOOR)
            exp.append(e)
            continue

        pts = 0
        mx = 0
        if use_st:
            mx += 1
            pts += int(r['stb'])
        if use_macd:
            mx += 2
            pts += int(r['mh'] > 0) + int(r['ml'] > 0)
        if use_rsi:
            mx += 1
            pts += int(r['rsi'] > 50)

        # Full V1.6 uses 3 of 4 points for B. In ablations, keep the same
        # "roughly 75% of available momentum checks are bullish" threshold.
        need = int(np.ceil(0.75 * mx)) if mx else 999
        e = MAX_EXPOSURE if pts >= need else 1.0
        if e > 1.0 and not r['lok']:
            e = 1.0
        e = min(e, MAX_EXPOSURE)
        if valid:
            e = max(0.0, min(2.0, e * scale))
        exp.append(e)

    sig = np.round(np.array(exp) * 20).astype(int)
    confsig = confirm(sig.tolist(), CONFIRM)
    db = int(round(DEADBAND * 20))
    held = confsig[0]
    ded = []
    for v in confsig:
        if abs(v - held) >= db:
            held = v
        ded.append(held)

    e = np.array(ded) / 20.0
    q = np.where(e <= 1.0, e, 2.0 - e)
    l = np.where(e <= 1.0, 0.0, e - 1.0)
    cash = 1.0 - q - l
    return pd.DataFrame({'q': q, 'l': l, 'c': cash}, index=ind.index).shift(1).bfill()


RQ = rq.loc[TRADE_INDEX].values
RL = rl.loc[TRADE_INDEX].values
RF = rf.loc[TRADE_INDEX].values


def run(Wc):
    Wc = Wc.loc[TRADE_INDEX]
    val = 1.0
    wq = wl = wc = 0.0
    ptq = ptl = None
    eq = []
    exps = []
    turns = []
    Q = Wc['q'].values
    L = Wc['l'].values
    C = Wc['c'].values
    for i in range(len(Wc)):
        tq, tl, tc = Q[i], L[i], C[i]
        turn = 0.0
        if ptq is None or abs(tq - ptq) > 1e-9 or abs(tl - ptl) > 1e-9:
            turn = abs(tq - wq) + abs(tl - wl)
            val *= (1 - turn * COST)
            wq, wl, wc = tq, tl, tc
            ptq, ptl = tq, tl
        val *= (1 + wq * RQ[i] + wl * RL[i] + wc * RF[i])
        eq.append(val)
        exps.append(wq + 2 * wl)
        turns.append(turn)
        nq = wq * (1 + RQ[i])
        nl = wl * (1 + RL[i])
        nc = wc * (1 + RF[i])
        tot = nq + nl + nc
        if tot > 0:
            wq, wl, wc = nq / tot, nl / tot, nc / tot
    return pd.Series(eq, index=Wc.index), pd.Series(exps, index=Wc.index), pd.Series(turns, index=Wc.index)


def met(e):
    e = e.dropna()
    r = e.pct_change().dropna()
    yrs = len(e) / 252
    cagr = e.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(252)
    shp = r.mean() * 252 / vol if vol > 0 else 0
    mdd = (e / e.cummax() - 1).min()
    cal = cagr / abs(mdd) if mdd < 0 else np.nan
    return cagr, mdd, cal, shp, e.iloc[-1] - 1


def sub(e, s='2006-06-22'):
    x = e[e.index >= s]
    return met(x / x.iloc[0])


configs = [
    ('V1.6 完整(3指标)', dict()),
    ('去掉 MACD', dict(use_macd=False)),
    ('去掉 RSI', dict(use_rsi=False)),
    ('去掉 Supertrend', dict(use_st=False)),
]

res = {}
print(f"{'配置':<20}{'年化':>7}{'总收益':>9}{'最大回撤':>9}{'Calmar':>8}{'夏普':>7}{'平均敞口':>9}{'年化换手':>9}")
for name, kw in configs:
    e, ex, turn = run(build(**kw))
    cg, md, cal, sh, tot = met(e)
    ann_turn = turn.sum() / (len(turn) / 252)
    res[name] = (cg, md, cal, sh, tot, ex.mean(), ann_turn)
    print(f"{name:<20}{cg*100:>6.1f}%{tot*100:>8.0f}%{md*100:>8.1f}%{cal:>8.2f}{sh:>7.2f}{ex.mean():>8.2f}x{ann_turn:>8.2f}")

print("\n--- 2006-06 后(全真实 QLD)---")
print(f"{'配置':<20}{'年化':>7}{'最大回撤':>9}{'Calmar':>8}")
for name, kw in configs:
    e, _, _ = run(build(**kw))
    cg, md, cal, sh, tot = sub(e)
    print(f"{name:<20}{cg*100:>6.1f}%{md*100:>8.1f}%{cal:>8.2f}")

base = res['V1.6 完整(3指标)']
print("\n相对完整版的变化:")
for name in ['去掉 MACD', '去掉 RSI', '去掉 Supertrend']:
    cg, md, cal, sh, tot, ae, at = res[name]
    print(f"  {name:<16} 年化 {(cg-base[0])*100:+.1f}pp  最大回撤 {(md-base[1])*100:+.1f}pp  Calmar {cal-base[2]:+.2f}")
