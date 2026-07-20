# -*- coding: utf-8 -*-
# V4.3 robustness / in-sample vs out-of-sample scan.
#
# This script intentionally keeps indicator construction inline because it scans
# indicator parameters. The strategy/execution defaults match 2_backtest.py V4.3:
# 250d gate, VOL_CAP=1.0, MAX_EXPOSURE=1.5, D=0.5x * vol target, 0.10x deadband,
# T+1 execution, and no rebalancing inside a held tier.
import os
import sys
import pandas as pd
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep
DATA = OUT + 'prices.csv'
if not os.path.exists(DATA):
    sys.exit('缺少 prices.csv: 请先运行 python 1_prepare_data.py')

df = pd.read_csv(DATA, parse_dates=['Date'], index_col='Date')
px = df['qqq']; high = df['qhigh']; low = df['qlow']
rq = df['qqq_ret']; rl = df['qld_ret']; rf = df['irx'] / 100.0 / 252.0

# ---------------- V4.3 baseline config ----------------
BASE_SMA = 250
BASE_VOLT = 0.20
BASE_VCAP = 1.0
BASE_MAXE = 1.5
BASE_ST_P = 10
BASE_ST_M = 3.0
BASE_RVOL_WIN = 20
BASE_LEV_CEIL = 0.40
BASE_CONFIRM = 3
BASE_DEADBAND = 0.10
COST = 5 / 10000
TRAIN_END = '2013-01-01'


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def indicators(sma_len=BASE_SMA, st_p=BASE_ST_P, st_m=BASE_ST_M, rvol_win=BASE_RVOL_WIN):
    macd_line = ema(px, 12) - ema(px, 26)
    macd_hist = macd_line - ema(macd_line, 9)

    d = px.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rsi = (100 - 100 / (1 + up.ewm(alpha=1/14, adjust=False).mean()
           / dn.ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan))).fillna(50)

    pc = px.shift(1)
    tr = pd.concat([(high-low), (high-pc).abs(), (low-pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/st_p, adjust=False).mean()
    hl2 = (high + low) / 2
    ub = (hl2 + st_m * atr).values
    lb = (hl2 - st_m * atr).values
    c = px.values
    n = len(px)
    fu = ub.copy()
    fl = lb.copy()
    direc = np.ones(n, int)
    for i in range(1, n):
        fu[i] = ub[i] if (ub[i] < fu[i-1] or c[i-1] > fu[i-1]) else fu[i-1]
        fl[i] = lb[i] if (lb[i] > fl[i-1] or c[i-1] < fl[i-1]) else fl[i-1]
        direc[i] = (-1 if c[i] < fl[i-1] else 1) if direc[i-1] == 1 else (1 if c[i] > fu[i-1] else -1)

    sma = px.rolling(sma_len).mean()
    macro = (px > sma).fillna(False)
    rising = (sma > sma.shift(20)).fillna(False)
    rvol = px.pct_change().rolling(rvol_win).std() * np.sqrt(252)
    return pd.DataFrame({
        'ml': macd_line, 'mh': macd_hist, 'rsi': rsi, 'stb': pd.Series(direc == 1, index=px.index),
        'macro': macro, 'rising': rising, 'rvol': rvol
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


def build(ind, volt=BASE_VOLT, vcap=BASE_VCAP, max_exposure=BASE_MAXE,
          lev_volceil=BASE_LEV_CEIL, confirm_k=BASE_CONFIRM,
          deadband=BASE_DEADBAND):
    ml = ind['ml'].values
    mh = ind['mh'].values
    rsi = ind['rsi'].values
    stb = ind['stb'].values.astype(bool)
    macro = ind['macro'].values.astype(bool)
    rising = ind['rising'].values.astype(bool)
    rvol = ind['rvol'].values

    score = stb.astype(int) + (mh > 0).astype(int) + (ml > 0).astype(int) + (rsi > 50).astype(int)
    lever_ok = rising & (rvol < lev_volceil)

    exp = np.where(score >= 3, max_exposure, 1.0)
    exp = np.where((exp > 1.0) & (~lever_ok), 1.0, exp)

    valid = (rvol > 0) & (~np.isnan(rvol))
    with np.errstate(divide='ignore', invalid='ignore'):
        scale = np.minimum(vcap, np.where(valid, volt / rvol, vcap))
    exp = np.where(valid, np.clip(exp * scale, 0.0, 2.0), exp)

    strong_bear = (~macro) & (ml < 0) & (~stb)
    mild_bear = (~macro) & (~strong_bear)
    d_exp = np.where(valid, np.clip(0.5 * scale, 0.0, 2.0), 0.5)
    exp = np.where(strong_bear, 0.0, exp)
    exp = np.where(mild_bear, d_exp, exp)

    sig = np.round(exp * 20).astype(int)
    confsig = confirm(sig.tolist(), confirm_k)

    db = int(round(deadband * 20))
    held = confsig[0]
    ded = []
    for v in confsig:
        if abs(v - held) >= db:
            held = v
        ded.append(held)

    e = np.array(ded) / 20.0
    q = np.where(e <= 1.0, e, 2.0 - e)
    l = np.where(e <= 1.0, 0.0, e - 1.0)
    c = 1.0 - q - l
    return pd.DataFrame({'q': q, 'l': l, 'c': c}, index=ind.index).shift(1).bfill()


RQ = rq.values
RL = rl.values
RF = rf.values


def run(Wc):
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
    return cagr, mdd, cal, shp


def seg(e, a, b):
    s = e[(e.index >= a) & (e.index < b)]
    s = s / s.iloc[0]
    return met(s)


base_ind = indicators()

print("=" * 96)
print(f"A) V4.3 波动率目标 volt × VOL_CAP 网格  —— 指标固定(SMA={BASE_SMA}), MAX_EXPOSURE={BASE_MAXE}")
print("   每格显示 全周期Calmar / 训练段(≤2012) / 验证段(2013+)；VOL_CAP<=1 表示只降不升")
print("=" * 96)
volts = [0.14, 0.16, 0.18, 0.20, 0.22, 0.25]
vcaps = [0.80, 0.90, 1.00]
print(f"{'volt|cap':>9}" + "".join(f"{v:>18}" for v in vcaps))
rob = {}
for vt in volts:
    row = f"{vt:>9}"
    for vc in vcaps:
        e, _, _ = run(build(base_ind, volt=vt, vcap=vc))
        cf = met(e)[2]
        ctr = seg(e, '1999-01-01', TRAIN_END)[2]
        cte = seg(e, TRAIN_END, '2027-01-01')[2]
        rob[(vt, vc)] = (cf, ctr, cte, met(e)[0], met(e)[1])
        row += f"  {cf:4.2f}/{ctr:4.2f}/{cte:4.2f}"
    print(row)

best = sorted(rob.items(), key=lambda kv: min(kv[1][1], kv[1][2]), reverse=True)[:5]
print("\n最稳健(训练&验证 Calmar 都高)的前 5 组:")
for (vt, vc), (cf, ctr, cte, cg, md) in best:
    print(f"  volt={vt} cap={vc:<4} | 全周期 CAGR {cg*100:4.1f}% 回撤 {md*100:5.1f}% Calmar {cf:.2f} | 训练 {ctr:.2f} 验证 {cte:.2f}")

print("\n" + "=" * 96)
print(f"B) V4.3 1D 敏感性(每次只动一个)  基准 SMA={BASE_SMA} volt={BASE_VOLT} cap={BASE_VCAP} max={BASE_MAXE}")
print("=" * 96)


def one(label, ind, **kw):
    e, ex, turn = run(build(ind, **kw))
    cg, md, cal, sh = met(e)
    ann_turn = turn.sum() / (len(turn) / 252)
    print(f"  {label:<26} CAGR {cg*100:5.1f}%  回撤 {md*100:6.1f}%  Calmar {cal:.2f}  夏普 {sh:.2f}  平均敞口 {ex.mean():.2f}x  年化换手 {ann_turn:.2f}")


print("· SMA 长度:")
for L in [120, 150, 200, 250, 300]:
    one(f"sma_len={L}", indicators(sma_len=L))
print("· Supertrend 倍数:")
for m in [2.0, 2.5, 3.0, 3.5, 4.0]:
    one(f"st_mult={m}", indicators(st_m=m))
print("· 波动率回看窗口:")
for w in [10, 15, 20, 30, 40]:
    one(f"rvol_win={w}", indicators(rvol_win=w))
print("· 确认天数:")
for k in [1, 2, 3, 5, 8]:
    one(f"confirm={k}", base_ind, confirm_k=k)
print("· 死区 deadband:")
for db in [0.00, 0.05, 0.10, 0.15, 0.20]:
    one(f"deadband={db:.2f}", base_ind, deadband=db)
print("· 加杠杆的波动天花板 lev_volceil:")
for cz in [0.30, 0.35, 0.40, 0.50, 0.99]:
    one(f"lev_volceil={cz}", base_ind, lev_volceil=cz)
