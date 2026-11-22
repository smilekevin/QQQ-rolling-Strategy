"""Verify EN / Simplified Chinese / Traditional Chinese i18n in qqq_qld_report.html."""

import json
from pathlib import Path
import re
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_HTML = REPO_ROOT / "qqq_qld_report.html"


def _extract_scripts(html: str) -> list[str]:
    return re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S)


class ReportI18nTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = REPORT_HTML.read_text("utf-8")
        cls.scripts = _extract_scripts(cls.html)

    def test_translations_cover_all_data_i18n_and_three_locales(self) -> None:
        match = re.search(r"const REPORT_TRANSLATIONS = (\[.*?\]);", self.html, flags=re.S)
        self.assertIsNotNone(match, "REPORT_TRANSLATIONS array not found")
        translations = json.loads(match.group(1))
        self.assertGreater(len(translations), 0)

        for idx, entry in enumerate(translations):
            self.assertEqual(
                set(entry.keys()),
                {"en", "zh-CN", "zh-TW"},
                f"Entry {idx} must define en, zh-CN and zh-TW keys",
            )
            for locale in ("en", "zh-CN", "zh-TW"):
                self.assertIsInstance(entry[locale], str)
                self.assertTrue(entry[locale], f"Empty {locale} string at index {idx}")

        indices = {int(value) for value in re.findall(r'data-i18n="(\d+)"', self.html)}
        self.assertGreater(len(indices), 0)
        for idx in indices:
            self.assertGreaterEqual(idx, 0)
            self.assertLess(idx, len(translations), f"data-i18n={idx} out of range")

    def test_switcher_markup_and_data_key_consistency(self) -> None:
        self.assertIn('data-lang="en"', self.html)
        self.assertIn('data-lang="zh-CN"', self.html)
        self.assertIn('data-lang="zh-TW"', self.html)
        self.assertNotIn("reportLanguage==='zh'", self.html)
        self.assertNotIn('reportLanguage==="zh"', self.html)

        statecol_match = re.search(r"const STATECOL = (\{.*?\});", self.html)
        decnm_match = re.search(r"const DECNM\s*=\s*(\{.*?\});", self.html)
        statetw_match = re.search(r"const STATETW\s*=\s*(\{.*?\});", self.html)
        stateen_match = re.search(r"const STATEEN\s*=\s*(\{.*?\});", self.html)
        self.assertIsNotNone(statecol_match)
        self.assertIsNotNone(decnm_match)
        self.assertIsNotNone(statetw_match)
        self.assertIsNotNone(stateen_match)

        statecol_keys = set(re.findall(r"'([^']+)'\s*:", statecol_match.group(1)))
        decnm_values = set(re.findall(r":\s*'([^']+)'", decnm_match.group(1)))
        statetw_keys = set(re.findall(r"'([^']+)'\s*:", statetw_match.group(1)))
        stateen_keys = set(re.findall(r"'([^']+)'\s*:", stateen_match.group(1)))

        self.assertEqual(statecol_keys, decnm_values)
        self.assertEqual(statetw_keys, decnm_values)
        self.assertEqual(stateen_keys, decnm_values)

    def test_inline_scripts_have_valid_javascript_syntax(self) -> None:
        inline_scripts = [body for body in self.scripts if body.strip()]
        self.assertGreaterEqual(len(inline_scripts), 3)
        for index, body in enumerate(inline_scripts):
            result = subprocess.run(
                ["node", "--input-type=commonjs", "-e", "new Function(process.argv[1]);", body],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"Inline script #{index} syntax error: {result.stderr}",
            )

    def test_browser_detection_persistence_and_switching_in_node(self) -> None:
        i18n_script = next(
            body for body in self.scripts if "const REPORT_TRANSLATIONS" in body
        )
        harness = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const i18nScript = process.argv[1];

function runScenario({ languages, language, saved, throwStorage = false }) {
  const store = new Map();
  if (saved !== undefined) store.set('qqq-report-language', saved);

  const elementsById = {};
  const makeEl = (id, attrs = {}) => {
    const el = {
      id,
      attrs: { ...attrs },
      dataset: {},
      textContent: '',
      innerHTML: '',
      listeners: {},
      children: [],
      setAttribute(k, v) { this.attrs[k] = String(v); },
      getAttribute(k) { return this.attrs[k]; },
      addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); },
      querySelectorAll(sel) {
        if (sel === 'button[data-lang]') return this.children;
        return [];
      },
      closest(sel) {
        if (sel === 'button[data-lang]' && this.dataset.lang) return this;
        return null;
      },
    };
    if (id) elementsById[id] = el;
    return el;
  };

  for (const id of ['dstart', 'dend', 'ddstart', 'ddend', 'eqchart', 'ddchart', 'distchart', 'expchart']) {
    makeEl(id);
  }
  const switcher = makeEl('language-switch');
  for (const code of ['en', 'zh-CN', 'zh-TW']) {
    const btn = makeEl('');
    btn.dataset.lang = code;
    switcher.children.push(btn);
  }
  const errEl = makeEl('report-error');
  const titleEl = makeEl('');
  titleEl.dataset.i18n = '0';
  const langLabelEl = makeEl('');
  langLabelEl.dataset.i18n = '140';

  const events = [];
  const docEl = { lang: 'en' };
  const localStorage = {
    getItem(k) {
      if (throwStorage) throw new Error('blocked');
      return store.has(k) ? store.get(k) : null;
    },
    setItem(k, v) {
      if (throwStorage) throw new Error('blocked');
      store.set(k, String(v));
    },
  };

  const context = {
    navigator: { languages, language },
    localStorage,
    document: {
      documentElement: docEl,
      querySelectorAll(sel) {
        if (sel === '[data-i18n]') return [titleEl, langLabelEl];
        return [];
      },
      getElementById(id) { return elementsById[id] || null; },
    },
    window: {
      dispatchEvent(ev) { events.push(ev.type); },
    },
    Event: class Event { constructor(type) { this.type = type; } },
  };

  vm.runInNewContext(i18nScript, context);
  return {
    docEl,
    titleEl,
    langLabelEl,
    errEl,
    switcher,
    store,
    events,
    click(code) {
      const btn = switcher.children.find(b => b.dataset.lang === code);
      switcher.listeners.click.forEach(fn => fn({ target: btn }));
    },
  };
}

// Browser detection cases
const cases = [
  [{ languages: ['en-US', 'zh-TW'], language: 'en-US' }, 'en'],
  [{ languages: ['ja-JP'], language: 'ja-JP' }, 'en'],
  [{ languages: [], language: '' }, 'en'],
  [{ languages: ['zh'], language: 'zh' }, 'zh-CN'],
  [{ languages: ['zh-CN', 'en'], language: 'zh-CN' }, 'zh-CN'],
  [{ languages: ['zh-SG'], language: 'zh-SG' }, 'zh-CN'],
  [{ languages: ['zh-Hans'], language: 'zh-Hans' }, 'zh-CN'],
  [{ languages: ['zh-Hans-TW'], language: 'zh-Hans-TW' }, 'zh-CN'],
  [{ languages: ['zh_CN'], language: 'zh_CN' }, 'zh-CN'],
  [{ languages: ['zh-TW', 'zh', 'en'], language: 'zh-TW' }, 'zh-TW'],
  [{ languages: ['zh-HK'], language: 'zh-HK' }, 'zh-TW'],
  [{ languages: ['zh-MO'], language: 'zh-MO' }, 'zh-TW'],
  [{ languages: ['zh-Hant'], language: 'zh-Hant' }, 'zh-TW'],
  [{ languages: ['zh-Hant-TW'], language: 'zh-Hant-TW' }, 'zh-TW'],
  [{ languages: ['zh-Hant-HK'], language: 'zh-Hant-HK' }, 'zh-TW'],
  [{ languages: ['zh_TW'], language: 'zh_TW' }, 'zh-TW'],
];
for (const [nav, expected] of cases) {
  const res = runScenario(nav);
  assert.equal(res.docEl.lang, expected, `Browser ${JSON.stringify(nav)} -> ${expected}`);
}

// Saved manual preference overrides browser language
assert.equal(runScenario({ languages: ['zh-TW'], saved: 'en' }).docEl.lang, 'en');
assert.equal(runScenario({ languages: ['en-US'], saved: 'zh-CN' }).docEl.lang, 'zh-CN');
assert.equal(runScenario({ languages: ['en-US'], saved: 'zh-TW' }).docEl.lang, 'zh-TW');

// Legacy saved 'zh' maps to zh-TW for TC browser, zh-CN otherwise
assert.equal(runScenario({ languages: ['zh-TW'], saved: 'zh' }).docEl.lang, 'zh-TW');
assert.equal(runScenario({ languages: ['en-US'], saved: 'zh' }).docEl.lang, 'zh-CN');

// Switching updates DOM, aria-pressed, error card, and localStorage
const s = runScenario({ languages: ['en-US'] });
assert.equal(s.titleEl.textContent, 'QQQ/QLD Dynamic Allocation Backtest V1.7.0');
assert.equal(s.langLabelEl.textContent, 'Language');

s.click('zh-CN');
assert.equal(s.docEl.lang, 'zh-CN');
assert.equal(s.store.get('qqq-report-language'), 'zh-CN');
assert.equal(s.titleEl.textContent, 'QQQ/QLD 动态滚仓策略回测 V1.7.0');
assert.equal(s.langLabelEl.textContent, '语言');
assert.match(s.errEl.innerHTML, /缺少报告数据/);
assert.deepEqual(s.switcher.children.map(b => b.getAttribute('aria-pressed')), ['false', 'true', 'false']);
assert.equal(s.events.length, 1);

s.click('zh-TW');
assert.equal(s.docEl.lang, 'zh-TW');
assert.equal(s.store.get('qqq-report-language'), 'zh-TW');
assert.equal(s.titleEl.textContent, 'QQQ/QLD 動態滾倉策略回測 V1.7.0');
assert.equal(s.langLabelEl.textContent, '語言');
assert.match(s.errEl.innerHTML, /缺少報告數據/);
assert.deepEqual(s.switcher.children.map(b => b.getAttribute('aria-pressed')), ['false', 'false', 'true']);
assert.equal(s.events.length, 2);

// Clicking current language does not emit redundant change event
s.click('zh-TW');
assert.equal(s.events.length, 2);

// Storage errors do not break initial detection or switching
const noStorage = runScenario({ languages: ['zh-HK'], throwStorage: true });
assert.equal(noStorage.docEl.lang, 'zh-TW');
noStorage.click('en');
assert.equal(noStorage.docEl.lang, 'en');
assert.equal(noStorage.events.length, 1);
"""
        result = subprocess.run(
            ["node", "-e", harness, i18n_script],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, f"Node test failed:\n{result.stderr}")

    def test_full_report_rendering_switches_between_three_locales(self) -> None:
        inline_scripts = [body for body in self.scripts if body.strip()]
        i18n_script = inline_scripts[1]
        main_script = inline_scripts[2]
        harness = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const i18nScript = process.argv[1];
const mainScript = process.argv[2];

const byId = {};
const makeEl = (id = '') => {
  const classes = new Set();
  const el = {
    id, attrs: {}, dataset: {}, style: { setProperty() {} },
    textContent: '', innerHTML: '', value: '', min: '', max: '', hidden: false,
    className: '',
    classList: {
      add(c) { classes.add(c); },
      remove(c) { classes.delete(c); },
      toggle(c, f) { f ? classes.add(c) : classes.delete(c); },
      contains(c) { return classes.has(c); },
    },
    listeners: {}, children: [],
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k]; },
    addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); },
    querySelectorAll(sel) { return sel === 'button[data-lang]' ? this.children : []; },
    closest(sel) { return sel === 'button[data-lang]' && this.dataset.lang ? this : makeEl(); },
    after(node) {
      if (node.innerHTML && node.innerHTML.includes('metric-title')) {
        makeEl('metric-title'); makeEl('tbnote'); makeEl('mtab');
      }
    },
    getBoundingClientRect() { return { left: 0, width: 500 }; },
    clientWidth: 500,
  };
  if (id) byId[id] = el;
  return el;
};

[
  'hero-card','ldate','lstate','lstatebar','lreb','lind','turn','avgexp',
  'kpi','kpinote','dstart','dend','dapply','zreset','rangelabel',
  'ddstart','ddend','ddapply','ddreset','ddrangelabel',
  'exprangelabel','expreset','annualtable','annualnote',
  'eqchart','ddchart','distchart','expchart','statelegend','eqlegend','ddlegend','foot','eq-color-mode'
].forEach(makeEl);

const switcher = makeEl('language-switch');
for (const code of ['en', 'zh-CN', 'zh-TW']) {
  const b = makeEl(); b.dataset.lang = code; switcher.children.push(b);
}
const kpiBtn = makeEl(); kpiBtn.dataset.p = 'sub'; kpiBtn.classList.add('on');
const annBtn = makeEl(); annBtn.dataset.m = 'return'; annBtn.classList.add('on');
const rangeAllBtn = makeEl(); rangeAllBtn.dataset.r = 'all'; rangeAllBtn.classList.add('on');

const winListeners = {};
const charts = [];
class MockChart {
  constructor(canvas, config) {
    this.canvas = canvas; this.data = config.data; this.options = config.options;
    this.chartArea = { left: 0, right: 500, top: 0, bottom: 200 };
    this._vis = {}; charts.push(this);
  }
  isDatasetVisible(i) { return this._vis[i] !== false; }
  setDatasetVisibility(i, v) { this._vis[i] = v; }
  update() {}
  resize() {}
}

const mockMetric = { cagr: 0.15, total: 5.0, vol: 0.2, sharpe: 0.9, mdd: -0.22, calmar: 0.68 };
const stratKey = '策略(V1.7.0)';
const metricsObj = {
  [stratKey]: mockMetric,
  'QQQ半仓': mockMetric,
  'QQQ全仓(=买入持有QQQ)': mockMetric,
  'QQQ+QLD(50/50)': mockMetric,
  'QLD全仓(=买入持有QLD)': mockMetric,
};
const R = {
  variant: 'V1.7.0',
  range: ['1999-03-11', '2026-10-19'],
  ann_switch: 11.4, avg_exp: 0.89,
  dates: ['2025-12-31', '2026-01-02', '2026-01-05'],
  equity: {
    strategy: [1.0, 1.02, 1.05], qqq: [1.0, 1.01, 1.03], qld: [1.0, 1.02, 1.06],
    blend: [1.0, 1.015, 1.045], half: [1.0, 1.005, 1.015],
  },
  state_exp: [1.0, 1.5, 1.0],
  decision: ['C', 'B', 'C'],
  panic_dates: ['2025-12-31'],
  dist: { '趋势向上': 0.45, '中性偏多': 0.30, '反转恢复': 0.06, '温和回调': 0.07, '超跌底仓': 0.05, '强空头/现金': 0.07 },
  metrics: metricsObj, metrics_sub: metricsObj, metrics_2010: metricsObj, metrics_2020: metricsObj, metrics_5y: metricsObj,
  latest: {
    date: '2026-01-05', dec: 'B', exp: 1.0, prev_exp: 1.5, executed_exp: 1.0,
    last_reb: '2026-01-02', days_since: 3, price: 500, sma250: 420,
    macro_bull: true, deep_bear: false, oversold_latch: false,
    sma250_extension: 0.19, extension_cap_active: true, extension_release_threshold: 0.10,
    st_level: 480, st_bull: true, macd_hist: 1.2, macd_line: 3.4, rsi: 62.5, vix: 18.2,
    extreme_panic: false, rvol: 0.18,
  },
};

const store = new Map();
const context = {
  Chart: MockChart, console, setTimeout, clearTimeout,
  requestAnimationFrame: fn => fn(),
  navigator: { languages: ['zh-TW'], language: 'zh-TW' },
  localStorage: {
    getItem: k => store.has(k) ? store.get(k) : null,
    setItem: (k, v) => store.set(k, v),
  },
  document: {
    documentElement: { lang: 'en' },
    createElement: () => makeEl(),
    getElementById: id => byId[id] || null,
    querySelector: sel => {
      if (sel === '#kpitog button.on') return kpiBtn;
      if (sel === '#annualtog button.on') return annBtn;
      if (sel === '#rangetog button[data-r=all]') return rangeAllBtn;
      if (sel === '.kpi') return byId.kpi;
      return makeEl();
    },
    querySelectorAll: () => [],
  },
  Event: class Event { constructor(type) { this.type = type; } },
};
context.window = {
  REPORT_DATA_READY: Promise.resolve(),
  QQQ_REPORT_DATA: R,
  addEventListener: (type, fn) => (winListeners[type] ||= []).push(fn),
  dispatchEvent: ev => (winListeners[ev.type] || []).forEach(fn => fn(ev)),
};

(async () => {
  vm.runInNewContext(i18nScript, context);
  vm.runInNewContext(mainScript, context);
  await new Promise(r => setTimeout(r, 20));

  assert.equal(context.document.documentElement.lang, 'zh-TW');
  assert.equal(byId.lstate.textContent, '趨勢向上');
  assert.match(byId.lstatebar.innerHTML, /建議淨敞口/);
  assert.match(byId.lreb.innerHTML, /上次開盤調倉/);
  assert.match(byId.lreb.innerHTML, /過熱鎖存/);
  assert.match(byId.foot.innerHTML, /數據：QQQ/);
  assert.deepEqual(Array.from(charts[2].data.labels), ['趨勢向上', '中性偏多', '反轉恢復', '溫和回調', '超跌底倉', '強空頭/現金']);
  assert.equal(charts[3].data.datasets[0].label, '淨敞口');
  assert.equal(byId.rangelabel.textContent, '2025-12-31 → 2026-01-05 · 起點 = 1x');
  assert.equal(byId.ddrangelabel.textContent, '2025-12-31 → 2026-01-05 · 起點 = 0%');

  switcher.listeners.click.forEach(fn => fn({ target: switcher.children[1] }));
  assert.equal(context.document.documentElement.lang, 'zh-CN');
  assert.equal(byId.lstate.textContent, '趋势向上');
  assert.match(byId.lstatebar.innerHTML, /建议净敞口/);
  assert.match(byId.foot.innerHTML, /数据:QQQ/);
  assert.deepEqual(Array.from(charts[2].data.labels), ['趋势向上', '中性偏多', '反转恢复', '温和回调', '超跌底仓', '强空头/现金']);
  assert.equal(charts[3].data.datasets[0].label, '净敞口');
  assert.equal(byId.rangelabel.textContent, '2025-12-31 → 2026-01-05 · 起点 = 1x');

  switcher.listeners.click.forEach(fn => fn({ target: switcher.children[0] }));
  assert.equal(context.document.documentElement.lang, 'en');
  assert.equal(byId.lstate.textContent, 'Uptrend');
  assert.match(byId.lstatebar.innerHTML, /Target net exposure/);
  assert.match(byId.foot.innerHTML, /Data: QQQ/);
  assert.deepEqual(Array.from(charts[2].data.labels), ['Uptrend', 'Neutral bullish', 'Reversal recovery', 'Mild pullback', 'Oversold floor', 'Deep bear / cash']);
  assert.equal(charts[3].data.datasets[0].label, 'Net exposure');
  assert.equal(byId.rangelabel.textContent, '2025-12-31 → 2026-01-05 · Start = 1x');

  switcher.listeners.click.forEach(fn => fn({ target: switcher.children[2] }));
  assert.equal(context.document.documentElement.lang, 'zh-TW');
  assert.match(byId.mtab.innerHTML, /QQQ全倉\(=買入持有QQQ\)/);
  assert.match(byId.eqlegend.innerHTML, /圖例開關/);
  assert.match(byId.ddlegend.innerHTML, /圖例開關/);
  assert.match(byId.statelegend.innerHTML, /策略決策檔（懸浮看敞口）/);
})().catch(err => {
  console.error(err);
  process.exit(1);
});
"""
        result = subprocess.run(
            ["node", "-e", harness, i18n_script, main_script],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, f"Full report runtime test failed:\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
