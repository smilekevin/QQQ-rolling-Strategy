# Cloudflare 自动更新与部署

Worker 定时向 Pages Deploy Hook 发送 POST；Pages 拉取 Git 仓库并运行 Python 流水线，生成 `dist/` 后部署。Worker 日志中的“已触发”只表示构建请求成功，实际部署结果查看 Pages 的 Deployments。

## 1. 配置 Pages

先将本次新增的构建脚本、Worker 与说明文件提交并推送到你的 Git 仓库。无需提交 `prices.csv`、`results.json`、`report_data.js` 或 `dist/`。

在 Cloudflare 控制台进入 **Workers & Pages → 创建 Pages 项目 → 连接 Git 仓库**，选择本仓库和实际生产分支。

| 设置 | 值 |
|---|---|
| Framework preset | None |
| Root directory | 仓库根目录（留空） |
| Build command | `bash build_cloudflare.sh` |
| Build output directory | `dist` |
| 构建环境变量 `PYTHON_VERSION` | `3.12.10` |

已有 Git 集成的 Pages 项目可以直接修改上述构建设置。若之前使用手动上传创建项目，需要新建 Git 集成的 Pages 项目；两种模式不能直接切换。

构建会安装 `requirements.txt`，在临时目录依次运行 `1 → 2 → 3`，下载/行情检查失败时最多尝试三次。最新价格和报告日期/曲线长度检查通过后，只发布首页、原报告路径、`report_data.js` 和 `_headers`。失败构建不会替换现有线上版本。

第一次可在北京时间早上部署，避免在美股盘中拿到未完成的当日日线。脚本拒绝纽约时间 17:00 前的当日日线；行情超过七个自然日未更新也会失败。这是宽松的过期检查，没有交易所节假日日历，也不能保证每个源标的都已更新；实际数据可靠性需在 Pages 上跑通后观察。现有下载脚本对缺失数据的填充逻辑保持原样。

## 2. 创建 Pages Deploy Hook

进入 **你的 Pages 项目 → Settings → Builds → Add deploy hook**：

- 名称：`daily-market-update`（名称可自定）
- 分支：和生产部署分支一致

保存后复制 Hook URL。这个地址本身就能触发部署，应作为 Secret 保存，不要写进代码或 Git。

## 3. 部署定时 Worker（控制台方法）

1. 在 Workers & Pages 创建一个单独的 Worker，可命名为 `qqq-report-scheduler`。
2. 打开代码编辑器，将代码替换为本仓库的 `cloudflare/worker.mjs` 内容，点击 Deploy。
3. 进入 Worker 的 **Settings → Variables and Secrets**，添加 **Secret**：名称 `DEPLOY_HOOK_URL`，值为第 2 步的 Hook URL，保存并部署。
4. 进入 **Settings → Triggers → Cron Triggers**，添加 `30 22 * * MON-FRI`。

Cloudflare Cron 使用 UTC。UTC 周一至周五 22:30 对应**北京时间周二至周六 06:30**，为纽约夏令时 18:30、冬令时 17:30，距离常规收盘分别为 2.5 小时和 1.5 小时，符合脚本的 17:00 盘后校验门槛。周末和美国节假日不会自动识别交易日，可能重复发布相同交易日数据。Cron 修改可能需要最多 15 分钟生效。

这个 Worker 只处理 `scheduled` 事件，不提供通过访问网页手动触发部署的接口。

## 4. 部署定时 Worker（命令行方法，和控制台方法二选一）

本地需安装 Node.js。进入仓库根目录，执行：

```bash
npx wrangler@4 login
npx wrangler@4 deploy --config cloudflare/wrangler.jsonc
npx wrangler@4 secret put DEPLOY_HOOK_URL --config cloudflare/wrangler.jsonc
```

最后一条命令会提示输入 Secret，粘贴 Hook URL 即可。Wrangler 配置已经包含 Cron 和日志设置，且关闭公开的 `workers.dev` 地址。以后用 Wrangler 更新该 Worker 时，Cron 也继续在 `cloudflare/wrangler.jsonc` 中管理，避免控制台修改被下一次部署覆盖。

## 5. 验证与排查

- 先在 Pages 的 Deployments 手动重试一次部署，确认下载、回测、生成报告都成功，网站首页能显示最新交易日。
- 下一次定时时间后查看 Worker Logs，确认“Pages 构建已触发”，再查看 Pages 是否有来源为 Deploy Hook 的成功部署。
- Worker HTTP 报错：检查 Secret 是否正确，以及 Hook 是否被删除或关联到了错误项目。
- Worker 成功但网站没更新：查看 Pages 构建日志；Hook 返回成功不代表下载、构建或发布成功。
- 行情失败：查看下载日志；三次尝试仍失败时保留旧的线上报告，可在数据源恢复后手动重试部署。

只读查看实时 Worker 日志：

```bash
npx wrangler@4 tail --config cloudflare/wrangler.jsonc
```

暂停自动更新：控制台方法删除 Cron；Wrangler 方法将 `triggers.crons` 改为 `[]` 后重新部署。

官方文档：[Pages 构建](https://developers.cloudflare.com/pages/configuration/build-configuration/)、[Python 环境](https://developers.cloudflare.com/pages/configuration/build-image/)、[Deploy Hooks](https://developers.cloudflare.com/pages/configuration/deploy-hooks/)、[Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)、[Worker Secrets](https://developers.cloudflare.com/workers/configuration/secrets/)。
