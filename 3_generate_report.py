# -*- coding: utf-8 -*-
"""
第 3 步:把 results.json 转成交互式报告数据 report_data.js
运行: python 3_generate_report.py (需先跑完 2_backtest.py 生成 results.json)

qqq_qld_report.html 是固定页面壳;本脚本只更新 gitignored 的 report_data.js。
双击 HTML 即可打开;页面从本地 report_data.js 加载数据,并从 CDN 加载 Chart.js。
"""
import json
import os


OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep
DATAFILE = "report_data.js"

with open(OUT + "results.json", encoding="utf-8") as source:
    results = json.load(source)

data = json.dumps(results, ensure_ascii=False, separators=(",", ":"))
payload = "window.QQQ_REPORT_DATA = " + data + ";\n"

with open(OUT + DATAFILE, "w", encoding="utf-8") as output:
    output.write(payload)

print(f"{DATAFILE} bytes:", len(payload.encode("utf-8")))
