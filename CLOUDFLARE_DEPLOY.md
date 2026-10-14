# Cloudflare 自动更新：Worker + Wrangler + Workers Builds

一个 Worker 托管静态报告，并通过 Cron 调用自己的 Workers Builds Deploy Hook。构建环境运行现有 Python 流水线，再用 Wrangler 将 `dist/` 和 Worker 一起发布。

```text
北京时间周二至周六 06:30
  → Worker Cron → Workers Builds Hook
  → 拉取 Git 仓库 → 下载行情 → 回测 → 生成 dist/
  → Wrangler 发布此 Worker 和静态报告
```

`wrangler.jsonc` 位于仓库根目录，绑定 `dist/`，配置网站地址、静态资源和 Cron；`package.json` / `package-lock.json` 固定 Wrangler 依赖。Worker 源码为 `cloudflare/worker.mjs`。

## 1. 连接 Workers Builds

先将本次配置修改提交并推送到 Git。`prices.csv`、`results.json`、`report_data.js`、`dist/` 和 `node_modules/` 不需要提交。

进入 Cloudflare **Workers & Pages**，创建 Worker 并导入 `smilekevin/QQQ-rolling-Strategy`，或在已创建的 Worker 中连接此 Git 仓库。仓库不可见时，在 [GitHub 已安装应用](https://github.com/settings/installations) 中配置 Cloudflare Workers and Pages 的 Repository access，将本仓库加入授权范围。

| 设置 | 值 |
|---|---|
| Worker 名称 | `qqq-strategy-auto-deploy`，与 `wrangler.jsonc` 的 `name` 一致 |
| 生产分支 | `main` |
| Root directory | 仓库根目录，留空或使用默认值 |
| Build command | `bash build_cloudflare.sh` |
| Deploy command | `npm run deploy` |
| 构建环境变量 `PYTHON_VERSION` | `3.12.10` |

**Workers Builds 不需要填写 Build output directory**，`dist/` 已在 Wrangler 的 `assets.directory` 中配置。如果现有 Worker 名称不同，先将 `wrangler.jsonc` 的 `name` 改成该名称，再提交推送。

构建会安装 Python 依赖，在临时目录运行 `1 → 2 → 3`；最新行情与报告日期/曲线检查通过后，生成首页、原报告 HTML、`report_data.js` 和 `_headers`。下载/行情检查最多尝试三次。构建失败时不会发布新版本。

构建成功后，打开 Worker 页面显示的 `workers.dev` 地址，确认报告最新交易日。静态资源优先返回，`_headers` 负责 `report_data.js` 的重新验证；访问网页只读取报告，不会触发重新构建。

## 2. 创建此 Worker 的 Deploy Hook

进入 **同一个 Worker → Settings → Builds → Deploy Hooks**，创建 Hook：名称可填 `daily-market-update`，分支选 `main`，复制生成的 URL。地址格式如下：

```text
https://api.cloudflare.com/client/v4/workers/builds/deploy_hooks/<HOOK_ID>
```

进入 **Settings → Variables and Secrets**，添加类型为 **Secret** 的变量 `DEPLOY_HOOK_URL`，值为上述 URL，保存并部署。它是运行时 Secret，不是构建环境变量。

从原 Pages 方案迁移时，将已有 Secret 替换为当前 Worker 的 Workers Builds Hook。Worker 会在发送请求前检查地址格式，并检查 API 是否返回构建 ID；旧 Pages Hook 不适用于本方案。

## 3. 确认定时任务

`wrangler.jsonc` 已配置 `30 22 * * MON-FRI`，部署后可在 Worker 的 **Settings → Triggers → Cron Triggers** 中查看。以后通过 Wrangler 修改 Cron 时，在仓库配置中维护，避免控制台修改被后续部署覆盖。

Cloudflare Cron 使用 UTC。该表达式对应**北京时间周二至周六 06:30**，即纽约夏令时 18:30、冬令时 17:30。修改最多可能需要 15 分钟生效。

构建脚本拒绝纽约时间 17:00 前的当日日线，以及超过七个自然日未更新的行情。这是宽松的过期检查，没有交易所节假日日历，也不能保证每个源标的都已更新；原下载脚本的数据填充逻辑保持原样。美国节假日可能发布相同交易日数据。

## 4. 本地使用 Wrangler

本地需 Node.js 和安装了 `requirements.txt` 的 Python 环境。在仓库根目录执行：

```bash
npm ci
source .venv/bin/activate
npm run build
npx wrangler login
npm run deploy
```

如果没有 Python 虚拟环境，先运行 `python3 -m venv .venv`。`npm run build` 会安装依赖并生成静态报告；`npm run deploy` 发布已生成的报告。整个自动流程仍需完成第 1、2 步，连接 Workers Builds 并设置 Hook。

设置或替换运行时 Secret：

```bash
npx wrangler secret put DEPLOY_HOOK_URL
```

本地预览或只检查打包：

```bash
npm run dev
npm run check:deploy
```

## 5. 验证与排查

- 先确认第一次 Workers Builds 的构建和部署成功，网站能显示最新交易日。
- 下一次定时时间后，Worker Logs 应显示“Workers Builds 已触发”和构建 ID；然后在此 Worker 的 Builds 中确认该构建成功。Hook 请求成功只表示已创建构建。
- Git 仓库不可见：检查 GitHub App 的仓库授权，以及 Cloudflare 选中的 GitHub 账号。
- Worker 名称不匹配：将 Wrangler 的 `name` 与连接 Workers Builds 的 Worker 名称对齐。
- Hook 报错：检查 `DEPLOY_HOOK_URL` 是否来自此 Worker 的 Builds，并确认分支为 `main`。
- Worker 成功但网站未更新：查看 Builds 的 Python 下载、回测和部署日志。

只读查看实时日志：`npx wrangler tail`。暂停自动更新：将根目录配置的 `triggers.crons` 改为 `[]` 后重新部署。

官方文档：[Workers Builds 配置](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)、[Python 构建环境](https://developers.cloudflare.com/workers/ci-cd/builds/build-image/)、[Workers Builds Deploy Hooks](https://developers.cloudflare.com/workers/ci-cd/builds/deploy-hooks/)、[静态资源](https://developers.cloudflare.com/workers/static-assets/binding/)、[静态缓存响应头](https://developers.cloudflare.com/workers/static-assets/headers/)。
