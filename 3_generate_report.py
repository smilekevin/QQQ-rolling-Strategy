# -*- coding: utf-8 -*-
"""
第 3 步:把 results.json 渲染成自包含交互式报告 qqq_qld_report.html
运行:  python 3_generate_report.py   (需先跑完 2_backtest.py 生成 results.json)
产物是单个 HTML 文件,双击即可用浏览器打开;仅从 CDN 加载 Chart.js,其余全部内联。
"""
import os, json
OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep
R=json.load(open(OUT+'results.json'))
DATA=json.dumps(R, ensure_ascii=False)

CHART='<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js" integrity="sha384-iU8HYtnGQ8Cy4zl7gbNMOhsDTTKX02BTXptVP/vqAWIaTfM7isw76iyZCsjL2eVi" crossorigin="anonymous"></script>'

html = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>QQQ/QLD 动态滚仓策略回测</title>
{CHART}
<style>
:root{{color-scheme:light}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#f4f1ea;color:#1c2230;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1120px;margin:0 auto;padding:34px 22px 70px}}
.eyebrow{{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:#9a7b3f;font-weight:700}}
h1{{font-size:30px;font-weight:800;letter-spacing:-.02em;margin:6px 0 4px}}
.sub{{color:#5a6172;font-size:14.5px;max-width:760px}}
.card{{background:#fffdf8;border:1px solid #e5ddcb;border-radius:14px;padding:22px 24px;margin-top:22px;box-shadow:0 1px 2px rgba(40,30,10,.04)}}
h2{{font-size:18px;font-weight:750;margin-bottom:3px;display:flex;align-items:center;gap:9px}}
h2 .n{{font-size:11px;background:#1c2230;color:#f4f1ea;width:22px;height:22px;border-radius:6px;display:inline-flex;align-items:center;justify-content:center;font-weight:700}}
.note{{color:#6a7183;font-size:13px;margin-bottom:14px}}
.signal{{display:flex;flex-wrap:wrap;gap:18px;align-items:center}}
.bigstate{{font-size:34px;font-weight:850;letter-spacing:-.02em;color:#1c2230}}
.pill{{display:inline-block;padding:4px 12px;border-radius:999px;font-size:12.5px;font-weight:700}}
.ind-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:6px;flex:1}}
.ind{{background:#faf6ec;border:1px solid #ece3d0;border-radius:10px;padding:10px 12px}}
.ind .k{{font-size:11px;color:#8a8570;text-transform:uppercase;letter-spacing:.08em}}
.ind .v{{font-size:18px;font-weight:750;margin-top:2px}}
.up{{color:#2f8f5b}} .dn{{color:#c2453b}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th,td{{padding:9px 8px;text-align:right;border-bottom:1px solid #eee4d2}}
th:first-child,td:first-child{{text-align:left}}
thead th{{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:#8a8570;border-bottom:1.5px solid #d9cfb8}}
tr.hl td{{background:#fbf4e3;font-weight:750}}
.best{{color:#2f8f5b;font-weight:750}}
.toggle{{display:inline-flex;background:#efe8d7;border-radius:9px;padding:3px;gap:2px;margin-bottom:12px}}
.toggle button{{border:0;background:transparent;padding:6px 15px;border-radius:7px;font-size:13px;font-weight:650;color:#6a7183;cursor:pointer;font-family:inherit}}
.toggle button.on{{background:#1c2230;color:#f4f1ea}}
.chartbox{{position:relative;height:380px;margin-top:6px}}
.chartbox.sm{{height:250px}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;font-size:12.5px;color:#5a6172;margin-top:10px}}
.legend span{{display:inline-flex;align-items:center;gap:6px}}
.dot{{width:11px;height:3px;border-radius:2px;display:inline-block}}
.rules{{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin-top:4px}}
.rule{{border:1px solid #e5ddcb;border-radius:11px;padding:13px 15px;background:#faf6ec}}
.rule .lv{{font-size:12px;font-weight:700;letter-spacing:.05em}}
.rule .ex{{font-size:22px;font-weight:800;margin:3px 0}}
.rule .ds{{font-size:12.5px;color:#5a6172}}
.two{{display:grid;grid-template-columns:1.35fr 1fr;gap:22px}}
@media(max-width:760px){{
  .two{{grid-template-columns:1fr}}
  .bigstate{{font-size:28px}}
  .wrap{{padding:20px 13px 54px}}
  h1{{font-size:23px}}
  .sub{{font-size:13.5px}}
  .card{{padding:16px 15px;border-radius:12px;margin-top:16px}}
  h2{{font-size:16px}}
  .chartbox{{height:300px}}
  .chartbox.sm{{height:230px}}
  table{{font-size:12.5px}} th,td{{padding:7px 5px}}
  .ind-grid{{grid-template-columns:repeat(auto-fit,minmax(96px,1fr))}}
  input[type=date]{{font-size:16px !important}}   /* 防 iOS 聚焦时自动放大 */
  .two{{gap:16px;margin-top:16px}}                 /* 竖直堆叠时与其他卡片间距一致 */
  .two .card{{margin-top:0}}                        /* 去掉叠加的 margin,避免间距偏大 */
}}
@media(max-width:430px){{
  .kpi{{grid-template-columns:repeat(2,1fr)}}
  .kpi .box .v{{font-size:20px}}
  .rules{{grid-template-columns:1fr}}
  .toggle button{{padding:6px 10px;font-size:12px}}
  .legend{{font-size:11.5px;gap:10px}}
}}
ul.rl{{margin:6px 0 0 2px;list-style:none;font-size:13.5px}}
ul.rl li{{padding:5px 0 5px 22px;position:relative;border-bottom:1px dashed #ece3d0}}
ul.rl li:before{{content:"▸";position:absolute;left:2px;color:#9a7b3f}}
code{{background:#efe8d7;padding:1px 6px;border-radius:5px;font-size:12.5px}}
.foot{{color:#8a8570;font-size:12px;margin-top:26px;line-height:1.7}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}}
.kpi .box{{background:#faf6ec;border:1px solid #ece3d0;border-radius:11px;padding:13px 15px}}
.kpi .box .k{{font-size:11px;color:#8a8570;text-transform:uppercase;letter-spacing:.07em}}
.kpi .box .v{{font-size:24px;font-weight:800;margin-top:2px;letter-spacing:-.02em}}
.kpi .box .s{{font-size:11.5px;color:#6a7183}}
</style></head>
<body><div class="wrap">
<div class="eyebrow">QQQ · QLD — 技术指标驱动的杠杆滚仓 · V4.2</div>
<h1>动态滚仓策略回测(V4.2 增强版)</h1>
<p class="sub">基于 QQQ 的 <b>MACD / RSI / Supertrend</b> + 250 日趋势闸门决定仓位档位,叠加 <b>20% 波动率目标</b>与<b>强空头清仓</b>两层风控,并让避险现金赚取短端国债收益。经样本内外验证优化(趋势闸门 250 日、波动率目标只降不升、去掉不赚风险溢价的 QLD全仓2x 档):全周期年化 12.4%、最大回撤压缩至 −30%,Calmar 达 0.41、夏普 0.71(全场最优),总收益反超买入持有 QQQ。净敞口在 <b>0(现金)→ 1.5x(QQQ+QLD)</b> 间连续调节。<b>档位持有期内不做再平衡</b>,且设 <b>0.10x 死区</b>——目标偏离当前持仓不足 0.10x 时不动手,与实盘操作一致。</p>

<!-- 当前信号 -->
<div class="card"><h2><span class="n">◆</span>当前建议仓位</h2>
<div class="note">截至 <b id="ldate"></b> 收盘,依据最新指标状态。仅供研究参考,非投资建议。</div>
<div class="signal">
  <div style="min-width:180px">
    <div class="bigstate" id="lstate"></div>
    <div id="lstatebar" style="margin-top:8px"></div>
    <div id="lreb" style="margin-top:10px;font-size:12.5px;color:#6a7183;line-height:1.7"></div>
  </div>
  <div class="ind-grid" id="lind"></div>
</div></div>

<!-- 关键结论 -->
<div class="card"><h2><span class="n">1</span>核心结论</h2>
<div class="toggle" id="kpitog">
  <button data-p="sub" class="on">2006至今(真实QLD)</button>
  <button data-p="p2010">2010至今</button>
  <button data-p="p2020">2020至今</button>
  <button data-p="full">1999至今(全区间)</button>
</div>
<div class="kpi" id="kpi"></div>
<p class="note" style="margin-top:14px" id="kpinote"></p>
</div>

<!-- 净值曲线 -->
<div class="card"><h2><span class="n">2</span>净值增长曲线(对数刻度)</h2>
<div class="note">起始 = 1.0。<b>策略主线按当时所处仓位分段着色</b>,基准线为灰色参照。可缩放:点选预设区间、<b>手动选起止日期</b>,或在图上<b>拖拽框选</b>放大。</div>
<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:8px">
  <div class="toggle" id="rangetog">
    <button data-r="all" class="on">全部</button>
    <button data-r="2008">2008后</button>
    <button data-r="2015">2015后</button>
    <button data-r="2020">2020后</button>
    <button data-r="2022">2022后</button>
  </div>
  <button id="zreset" style="border:1px solid #d9cfb8;background:#fffdf8;border-radius:8px;padding:6px 13px;font-size:12.5px;font-weight:650;color:#6a7183;cursor:pointer;font-family:inherit">↺ 复位缩放</button>
</div>
<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px">
  <span style="font-size:12.5px;color:#6a7183;font-weight:650">自定义区间</span>
  <input type="date" id="dstart" style="border:1px solid #d9cfb8;background:#fffdf8;border-radius:7px;padding:5px 9px;font-size:12.5px;color:#1c2230;font-family:inherit">
  <span style="color:#8a8570">→</span>
  <input type="date" id="dend" style="border:1px solid #d9cfb8;background:#fffdf8;border-radius:7px;padding:5px 9px;font-size:12.5px;color:#1c2230;font-family:inherit">
  <button id="dapply" style="border:0;background:#1c2230;color:#f4f1ea;border-radius:7px;padding:6px 14px;font-size:12.5px;font-weight:650;cursor:pointer;font-family:inherit">应用</button>
  <span style="font-size:12px;color:#8a8570" id="rangelabel"></span>
</div>
<div class="chartbox" id="eqbox"><canvas id="eqchart"></canvas></div>
<div class="legend" id="statelegend" style="margin-top:12px"></div>
<div class="legend" id="eqlegend"></div>
</div>

<div class="two">
<!-- 回撤 -->
<div class="card"><h2><span class="n">3</span>回撤对比</h2>
<div class="note">策略把 QLD 买入持有 -99% 的回撤压缩到显著更浅。</div>
<div class="chartbox sm"><canvas id="ddchart"></canvas></div>
</div>
<!-- 仓位分布 -->
<div class="card"><h2><span class="n">4</span>各档敞口时间占比</h2>
<div class="note">按净敞口分档统计。约 19% 时间完全避险(现金),约 41% 时间加杠杆(≥1.5x)。</div>
<div class="chartbox sm"><canvas id="distchart"></canvas></div>
</div>
</div>

<!-- 杠杆暴露 -->
<div class="card"><h2><span class="n">5</span>净杠杆暴露随时间变化</h2>
<div class="note">数值 = 组合对 QQQ 的等效敞口(0x 现金 → 2.0x QLD全仓),经波动率目标连续调节。可见熊市(2000、2008、2020、2022)自动降到现金或半仓。</div>
<div class="chartbox sm"><canvas id="expchart"></canvas></div>
</div>

<!-- 策略规则 -->
<div class="card"><h2><span class="n">6</span>切换规则</h2>
<div class="note">决策链:①先用 250 日均线定多空 → ②多头区间用 Supertrend/MACD/RSI 打分(0–4)定<b>基础档</b> → ③用 20% 波动率目标把基础档<b>连续缩放</b>成最终敞口 → ④强空头直接清仓。避险现金买短端国债生息。<b>V4.2 起去掉 QLD全仓2x 档,最高 1.5x。</b><br><span style="color:#b06a2e">⚠ 下面 B–E 是"决策档",给的是<b>基础(名义)敞口</b>;曲线配色与占比图按<b>最终净敞口</b>分区,两者经波动率目标缩放后不等同——例如高波动时 C 档(1.0x)会被缩到约 0.75x,显示成"半仓"色带,<b>此时价格其实仍在 250 日线上方,并非跌破</b>。</span></div>
<div class="rules">
 <div class="rule"><div class="lv" style="color:#6a9b3f">B · 趋势向上(最高档)</div><div class="ex">基础 1.5x · QQQ+QLD</div><div class="ds">动量 3–4 分,趋势健康。50% QQQ + 50% QLD;需 SMA250 上行 + 波动率&lt;40% 熔断许可。</div></div>
 <div class="rule"><div class="lv" style="color:#b8912f">C · 中性偏多</div><div class="ex">基础 1.0x · QQQ全仓</div><div class="ds">价在 SMA250 上方、动量一般(0–2 分),或杠杆熔断触发。</div></div>
 <div class="rule"><div class="lv" style="color:#c2453b">D · 温和回调</div><div class="ex">基础 0.5x · QQQ半仓</div><div class="ds">价跌破 250 日线但未确认空头 → 半仓 QQQ + 半仓现金生息。</div></div>
 <div class="rule"><div class="lv" style="color:#5a6172">E · 强空头</div><div class="ex">0x · 现金</div><div class="ds">跌破 250 日线 且 MACD&lt;0 且 Supertrend 空头 → 清仓避险,现金买国债。</div></div>
 <div class="rule" style="background:#eef4ee;border-color:#c9e0c9"><div class="lv" style="color:#2f6f4f">★ 波动率目标</div><div class="ex">×min(1.0, 20%÷实际波动)</div><div class="ds">把基础档连续缩放:波动飙升自动砍杠杆(只降不升)。所以最终敞口是连续值、落在哪个色带都可能。</div></div>
</div>
<ul class="rl">
 <li><b>宏观闸门:</b> 收盘价 vs 250 日均线,定多空大方向(经样本内外验证由 200 日优化而来)。</li>
 <li><b>动量打分(多头区间):</b> Supertrend 多头 +1、MACD 柱&gt;0 +1、MACD 线&gt;0 +1、RSI&gt;50 +1;0–2 分→QQQ全仓,3–4 分→QQQ+QLD(1.5x 封顶,MAX_EXPOSURE=1.5)。</li>
 <li><b>波动率目标(核心):</b> 最终敞口 = 档位敞口 ×min(1.0, 20%÷近20日年化波动率),0–2x 封顶(只降不升)。2000/2008/2020 波动暴涨时自动大幅降杠杆,躲开杠杆 ETF 最致命的深亏。</li>
 <li><b>强空头清仓:</b> 跌破 250 日线且 MACD&lt;0 且 Supertrend 空头时,直接 100% 现金(买国债),而非半仓硬扛。</li>
 <li><b>抗抖动:</b> 敞口按 0.05 档、连续 <code>3</code> 日确认;再设 <code>0.10x</code> 死区(目标偏离当前持仓 &lt;0.10x 则不动),信号 T 日生成、T+1 执行(无未来函数)。全周期换手约 <span id="turn"></span> 次/年,平均净敞口 <span id="avgexp"></span>x。</li>
</ul>
</div>

<div class="foot" id="foot"></div>
</div>

<script>
const R = {DATA};
const fmtP = x => (x*100).toFixed(1)+'%';
const fmtP0 = x => (x*100).toFixed(0)+'%';
const NAMES = ['策略(V4.2动态滚仓)','QQQ半仓','QQQ全仓(=买入持有QQQ)','QQQ+QLD(50/50)','QLD全仓(=买入持有QLD)'];
const COL = {{'策略(V4.2动态滚仓)':'#1c2230','QQQ半仓':'#c2453b','QQQ全仓(=买入持有QQQ)':'#c99a2e','QQQ+QLD(50/50)':'#3f7fb8','QLD全仓(=买入持有QLD)':'#9a7b3f'}};
const STATECOL = {{'QLD全仓':'#2f8f5b','QQQ+QLD':'#6a9b3f','QQQ全仓':'#b8912f','QQQ半仓':'#c2453b','现金/避险':'#5a6172'}};
// continuous net-exposure -> color band
function expColor(v){{ if(v<0.25)return '#5a6172'; if(v<0.75)return '#c2453b'; if(v<1.25)return '#b8912f'; if(v<1.75)return '#6a9b3f'; return '#2f8f5b'; }}
function expName(v){{ if(v<0.25)return '现金/避险 '+v.toFixed(2)+'x'; if(v<0.75)return 'QQQ半仓区 '+v.toFixed(2)+'x'; if(v<1.25)return 'QQQ全仓区 '+v.toFixed(2)+'x'; if(v<1.75)return 'QQQ+QLD区 '+v.toFixed(2)+'x'; return 'QLD全仓区 '+v.toFixed(2)+'x'; }}

// ---- latest signal ----
const L=R.latest;
document.getElementById('ldate').textContent=L.date;
document.getElementById('lstate').textContent=L.state;
document.getElementById('lstate').style.color=expColor(L.exp);
document.getElementById('lstatebar').innerHTML='<span class="pill" style="background:'+expColor(L.exp)+'22;color:'+expColor(L.exp)+'">建议净敞口 '+L.exp.toFixed(2)+'x</span>';
document.getElementById('lreb').innerHTML=
  '上次调仓:<b>'+L.last_reb+'</b>(距今 '+L.days_since+' 天)<br>'+
  '之前仓位:'+L.prev_state+' · '+L.prev_exp.toFixed(2)+'x  →  现 '+L.exp.toFixed(2)+'x';
const ind=[['价格',L.price.toFixed(0),''],['250日趋势',L.macro_bull?'多头':'空头',L.macro_bull?'up':'dn'],
 ['Supertrend',L.st_level.toFixed(0),L.st_bull?'up':'dn'],
 ['MACD 柱',L.macd_hist.toFixed(2),L.macd_hist>0?'up':'dn'],['MACD 线',L.macd_line.toFixed(2),L.macd_line>0?'up':'dn'],
 ['RSI(14)',L.rsi.toFixed(1),L.rsi>50?'up':'dn'],['20日波动率',(L.rvol*100).toFixed(0)+'%',L.rvol<0.4?'up':'dn']];
document.getElementById('lind').innerHTML=ind.map(([k,v,c])=>'<div class="ind"><div class="k">'+k+'</div><div class="v '+c+'">'+v+'</div></div>').join('');
document.getElementById('turn').textContent=R.ann_switch;
document.getElementById('avgexp').textContent=R.avg_exp;

// ---- KPI ----
const PMETA={{
  full:{{m:R.metrics,      label:'1999-03 至今(全区间)', span:'1999至今'}},
  sub :{{m:R.metrics_sub,  label:'2006-06 至今(真实QLD)', span:'2006至今'}},
  p2010:{{m:R.metrics_2010,label:'2010-01 至今',          span:'2010至今'}},
  p2020:{{m:R.metrics_2020,label:'2020-01 至今',          span:'2020至今'}},
}};
function renderKPI(period){{
 const meta=PMETA[period]||PMETA.sub; const M=meta.m;
 const s=M['策略(V4.2动态滚仓)'];
 const qqq=M['QQQ全仓(=买入持有QQQ)'], qld=M['QLD全仓(=买入持有QLD)'];
 const boxes=[
  ['年化收益',fmtP(s.cagr),'CAGR'],
  ['最大回撤',fmtP0(s.mdd),'峰值→谷底'],
  ['Calmar',s.calmar.toFixed(2),'年化/回撤'],
  ['夏普',s.sharpe.toFixed(2),'rf=0'],
  ['年化波动',fmtP(s.vol),''],
  ['总收益',fmtP0(s.total),meta.span],
 ];
 document.getElementById('kpi').innerHTML=boxes.map(([k,v,ss])=>'<div class="box"><div class="k">'+k+'</div><div class="v">'+v+'</div><div class="s">'+ss+'</div></div>').join('');
 let note='区间 '+meta.label+':策略 年化 '+fmtP(s.cagr)+'、回撤 '+fmtP0(s.mdd)+'、Calmar '+s.calmar.toFixed(2)
   +';同期买入持有 QQQ '+fmtP(qqq.cagr)+' / '+fmtP0(qqq.mdd)+',QLD '+fmtP(qld.cagr)+' / '+fmtP0(qld.mdd)+'。';
 if(period==='full') note+=' 注:含 2000–2002 泡沫破裂,且该段 QLD 为合成数据(偏乐观约 0.8%/年)。';
 document.getElementById('kpinote').textContent=note;
 renderTable(M, period);
}}
let tableCard=null;
function renderTable(M, period){{
 if(!tableCard){{
   tableCard=document.createElement('div'); tableCard.className='card';
   tableCard.innerHTML='<h2><span class="n">1b</span>完整指标对照</h2><div class="note" id="tbnote"></div><div style="overflow-x:auto"><table id="mtab"></table></div>';
   document.querySelector('.kpi').closest('.card').after(tableCard);
 }}
 const keys=NAMES;
 const cols=[['cagr','年化',fmtP],['total','总收益',fmtP0],['vol','波动',fmtP],['sharpe','夏普',x=>x.toFixed(2)],['mdd','最大回撤',fmtP0],['calmar','Calmar',x=>x.toFixed(2)]];
 // find best per col
 let best={{}};
 cols.forEach(([c])=>{{ let vals=keys.map(k=>M[k][c]); best[c]= (c==='mdd')? Math.max(...vals): Math.max(...vals); if(c==='vol') best[c]=Math.min(...vals); }});
 let h='<thead><tr><th>方案</th>'+cols.map(c=>'<th>'+c[1]+'</th>').join('')+'</tr></thead><tbody>';
 keys.forEach(k=>{{
   h+='<tr'+(k==='策略(V4.2动态滚仓)'?' class="hl"':'')+'><td>'+k+'</td>'+cols.map(([c,,f])=>{{
     let v=M[k][c]; let cls=(v===best[c])?' class="best"':''; return '<td'+cls+'>'+f(v)+'</td>';
   }}).join('')+'</tr>';
 }});
 h+='</tbody>';
 document.getElementById('mtab').innerHTML=h;
 document.getElementById('tbnote').textContent='区间 '+(PMETA[period]||PMETA.sub).label+'。绿色=该列最优。';
}}
document.querySelectorAll('#kpitog button').forEach(b=>b.onclick=()=>{{
 document.querySelectorAll('#kpitog button').forEach(x=>x.classList.remove('on'));
 b.classList.add('on'); renderKPI(b.dataset.p);
}});
renderKPI('sub');

// ---- equity chart : strategy line colored by active position ----
const D=R.dates;
const SE=R.state_exp;  // per-point exposure aligned to D
const EXPCOL={{0.5:'#c2453b',1.0:'#b8912f',1.5:'#6a9b3f',2.0:'#2f8f5b'}};
const EXPNAME={{0.5:'QQQ半仓 0.5x',1.0:'QQQ全仓 1.0x',1.5:'QQQ+QLD 1.5x',2.0:'QLD全仓 2.0x'}};
const stratDS={{
  label:'策略(V4.2动态滚仓)',data:R.equity.strategy,borderWidth:2.6,pointRadius:0,tension:.05,
  borderColor:'#1c2230',
  segment:{{ borderColor: ctx => expColor(SE[ctx.p1DataIndex]) }}
}};
function refline(name,arr){{return {{label:name,data:arr,borderColor:'#c9c0ac',backgroundColor:'#c9c0ac',borderWidth:1,pointRadius:0,tension:.05,borderDash: name.includes('QLD全仓')?[5,3]:(name.includes('QQQ全仓')?[]:[2,3])}};}}
const eqChart=new Chart(document.getElementById('eqchart'),{{type:'line',
 data:{{labels:D,datasets:[
   refline('QQQ全仓(=买入持有QQQ)',R.equity.qqq),
   refline('QLD全仓(=买入持有QLD)',R.equity.qld),
   refline('QQQ半仓',R.equity.half),
   stratDS,
 ]}},
 options:{{responsive:true,maintainAspectRatio:false,animation:false,interaction:{{mode:'index',intersect:false}},
   plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{
      title:items=>{{const i=items[0].dataIndex;return D[i]+'  ·  '+expName(SE[i]);}},
      label:c=>c.dataset.label+': '+c.parsed.y.toFixed(1)+'x'}}}}}},
   scales:{{x:{{type:'category',min:0,max:D.length-1,ticks:{{maxTicksLimit:10,color:'#8a8570'}},grid:{{display:false}}}},
     y:{{type:'logarithmic',ticks:{{color:'#8a8570',callback:v=>[1,3,10,30,100,300].includes(v)?v+'x':''}},grid:{{color:'#eee4d2'}}}}}}}}
}});
// state legend (what the colors mean) — continuous exposure bands
document.getElementById('statelegend').innerHTML='<b style="color:#5a6172">策略主线配色(按<b>最终净敞口</b>所在区间):</b>'+
  [['#6a9b3f','QQQ+QLD区 1.25–1.75x'],['#b8912f','QQQ全仓区 0.75–1.25x'],['#c2453b','半仓区 0.25–0.75x'],['#5a6172','现金/避险 0–0.25x']]
  .map(([c,t])=>'<span><i class="dot" style="background:'+c+'"></i>'+t+'</span>').join('');
document.getElementById('eqlegend').innerHTML='<b style="color:#5a6172">灰色参照:</b>'+
  '<span><i class="dot" style="background:#c9c0ac"></i>QQQ 买入持有</span>'+
  '<span><i class="dot" style="background:#c9c0ac;border-top:1px dashed #888"></i>QLD 买入持有(虚线)</span>'+
  '<span><i class="dot" style="background:#c9c0ac"></i>QQQ 半仓(点线)</span>';

// ---- zoom: preset ranges + drag-to-select ----
function idxForDate(y){{ for(let i=0;i<D.length;i++){{ if(+D[i].slice(0,4)>=y) return i; }} return 0; }}
// 日期字符串 -> 索引:start 取首个 >= 该日,end 取末个 <= 该日
function idxFromStr(str,isEnd){{
  if(isEnd){{ let r=D.length-1; for(let i=D.length-1;i>=0;i--){{ if(D[i]<=str){{r=i;break;}} }} return r; }}
  let r=0; for(let i=0;i<D.length;i++){{ if(D[i]>=str){{r=i;break;}} }} return r;
}}
const dStart=document.getElementById('dstart'), dEnd=document.getElementById('dend');
function setRange(a,b){{
  a=Math.max(0,Math.round(a)); b=Math.min(D.length-1,Math.round(b));
  if(b<a){{ const t=a;a=b;b=t; }}                  // 顺序颠倒则交换
  if(b-a<1) b=Math.min(D.length-1,a+1);            // 至少 2 个点即可(不再强制 ≥3)
  eqChart.options.scales.x.min=a; eqChart.options.scales.x.max=b; eqChart.update('none');
  document.getElementById('rangelabel').textContent=D[a]+' → '+D[b];
  dStart.value=D[a]; dEnd.value=D[b];            // 同步到日期选择器
}}
// 初始化日期选择器的可选范围与默认值
dStart.min=dEnd.min=D[0]; dStart.max=dEnd.max=D[D.length-1];
dStart.value=D[0]; dEnd.value=D[D.length-1];
document.querySelectorAll('#rangetog button').forEach(b=>b.onclick=()=>{{
  document.querySelectorAll('#rangetog button').forEach(x=>x.classList.remove('on')); b.classList.add('on');
  const r=b.dataset.r;
  if(r==='all') setRange(0,D.length-1); else setRange(idxForDate(+r),D.length-1);
}});
document.getElementById('dapply').onclick=()=>{{
  if(!dStart.value||!dEnd.value) return;
  let a=idxFromStr(dStart.value,false), b=idxFromStr(dEnd.value,true);
  document.querySelectorAll('#rangetog button').forEach(x=>x.classList.remove('on'));  // 取消预设高亮
  setRange(a,b);
}};
document.getElementById('zreset').onclick=()=>{{
  document.querySelectorAll('#rangetog button').forEach(x=>x.classList.remove('on'));
  document.querySelector('#rangetog button[data-r=all]').classList.add('on');
  setRange(0,D.length-1);
}};
// drag select on canvas —— 同时支持鼠标与触摸(手机)
(function(){{
  const cv=document.getElementById('eqchart'); let dragging=false,sx=0,cx=0;
  const box=document.getElementById('eqbox');
  const ov=document.createElement('div');
  ov.style.cssText='position:absolute;top:0;bottom:0;background:rgba(28,34,48,.10);border-left:1px solid #1c2230;border-right:1px solid #1c2230;pointer-events:none;display:none';
  box.style.position='relative'; box.appendChild(ov);
  function xToIdx(px){{ return eqChart.scales.x.getValueForPixel(px); }}
  const rectX=e=>{{ const r=cv.getBoundingClientRect(); const p=(e.touches?e.touches[0]:e); return p.clientX-r.left; }};
  cv.style.cursor='crosshair';
  function start(x){{ dragging=true; sx=x; cx=x; ov.style.left=x+'px'; ov.style.width='0px'; ov.style.display='block'; }}
  function move(x){{ if(!dragging)return; cx=x; ov.style.left=Math.min(sx,cx)+'px'; ov.style.width=Math.abs(cx-sx)+'px'; }}
  function end(){{ if(!dragging)return; dragging=false; ov.style.display='none';
    let a=xToIdx(Math.min(sx,cx)),b=xToIdx(Math.max(sx,cx));
    if(Math.abs(cx-sx)>8 && Math.abs(b-a)>=1){{ document.querySelectorAll('#rangetog button').forEach(x=>x.classList.remove('on')); setRange(a,b); }}
  }}
  cv.addEventListener('mousedown',e=>start(e.offsetX));
  cv.addEventListener('mousemove',e=>move(e.offsetX));
  window.addEventListener('mouseup',end);
  cv.addEventListener('touchstart',e=>{{ start(rectX(e)); }},{{passive:true}});
  cv.addEventListener('touchmove',e=>{{ if(dragging){{ e.preventDefault(); move(rectX(e)); }} }},{{passive:false}});
  cv.addEventListener('touchend',end);
}})();

// ---- drawdown ----
new Chart(document.getElementById('ddchart'),{{type:'line',
 data:{{labels:D,datasets:[
   {{label:'策略',data:R.drawdown.strategy,borderColor:'#1c2230',backgroundColor:'rgba(28,34,48,.10)',fill:true,borderWidth:1.6,pointRadius:0}},
   {{label:'QQQ买入持有',data:R.drawdown.qqq,borderColor:'#c99a2e',borderWidth:1,pointRadius:0}},
   {{label:'QLD买入持有',data:R.drawdown.qld,borderColor:'#9a7b3f',borderWidth:1,pointRadius:0,borderDash:[4,3]}},
 ]}},
 options:{{responsive:true,maintainAspectRatio:false,animation:false,
   plugins:{{legend:{{labels:{{boxWidth:12,font:{{size:11}}}}}},tooltip:{{mode:'index',intersect:false,callbacks:{{label:c=>c.dataset.label+': '+(c.parsed.y*100).toFixed(0)+'%'}}}}}},
   scales:{{x:{{ticks:{{maxTicksLimit:8,color:'#8a8570'}},grid:{{display:false}}}},y:{{ticks:{{color:'#8a8570',callback:v=>(v*100).toFixed(0)+'%'}},grid:{{color:'#eee4d2'}}}}}}}}
}});

// ---- distribution donut ----
// 只保留占比 > 0 的档位(如去掉 QLD全仓2x 后其占比为 0,不在图中出现)
const dEntries=Object.entries(R.dist).filter(([k,v])=>v>0.0005);
const dl=dEntries.map(e=>e[0]), dv=dEntries.map(e=>e[1]);
new Chart(document.getElementById('distchart'),{{type:'doughnut',
 data:{{labels:dl,datasets:[{{data:dv.map(x=>+(x*100).toFixed(1)),backgroundColor:dl.map(k=>STATECOL[k]),borderColor:'#fffdf8',borderWidth:2}}]}},
 options:{{responsive:true,maintainAspectRatio:false,cutout:'58%',
   plugins:{{legend:{{position:(window.innerWidth<560?'bottom':'right'),labels:{{boxWidth:12,font:{{size:12}}}}}},tooltip:{{callbacks:{{label:c=>c.label+': '+c.parsed+'%'}}}}}}}}
}});

// ---- exposure over time ----
new Chart(document.getElementById('expchart'),{{type:'line',
 data:{{labels:D,datasets:[{{label:'净敞口',data:R.exposure.vals,borderColor:'#3f7fb8',backgroundColor:'rgba(63,127,184,.12)',fill:true,borderWidth:1,pointRadius:0,stepped:true}}]}},
 options:{{responsive:true,maintainAspectRatio:false,animation:false,
   plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>'敞口 '+c.parsed.y.toFixed(1)+'x'}}}}}},
   scales:{{x:{{ticks:{{maxTicksLimit:10,color:'#8a8570'}},grid:{{display:false}}}},
     y:{{min:0,max:2.1,ticks:{{color:'#8a8570',stepSize:0.5,callback:v=>v.toFixed(1)+'x'}},grid:{{color:'#eee4d2'}}}}}}}}
}});

document.getElementById('foot').innerHTML=
 '数据:QQQ / QLD / ^IRX 复权收盘(yfinance),区间 '+R.range[0]+' 至 '+R.range[1]+'。'+
 '2006-06 前 QLD 由「2×QQQ 日收益 − (0.95% 费率 + 短端利率融资成本)/252」合成,与真实 QLD 重叠期日收益相关性 0.996、CAGR 偏乐观约 0.8%/年。'+
 '<br>V4.2 回测含 5bps/边 交易成本;避险现金按 ^IRX 短端国债利率计息;夏普用 rf=0。指标在 QQQ 上计算,信号 T 日收盘生成、T+1 执行。<b>档位持有期内不做再平衡</b>(QQQ/QLD 权重随行情漂移),仅在换档时按实际成交计成本——与实盘一致。'+
 '<br><b>重要:</b>历史回测不代表未来收益;杠杆 ETF 存在波动损耗与日度重置风险。本页面仅供研究与教育,非投资建议。';
</script>
</body></html>"""

open(OUT+'qqq_qld_report.html','w').write(html)
print("HTML bytes:",len(html))
