// 静态报告由 Workers Assets 托管；定时触发 Workers Builds 运行 Python 流水线。
export default {
  async fetch(request, env) {
    // 已有文件由静态资源服务优先返回；未匹配的请求按 ASSETS 的 404 规则处理。
    return env.ASSETS.fetch(request);
  },

  async scheduled(controller, env) {
    if (!env.DEPLOY_HOOK_URL) {
      throw new Error("请先配置 DEPLOY_HOOK_URL Secret");
    }

    let hook;
    try {
      hook = new URL(env.DEPLOY_HOOK_URL);
    } catch {
      throw new Error("DEPLOY_HOOK_URL 必须是有效的 Workers Builds Deploy Hook 地址");
    }
    if (
      hook.origin !== "https://api.cloudflare.com" ||
      !/^\/client\/v4\/workers\/builds\/deploy_hooks\/[^/]+$/.test(hook.pathname)
    ) {
      throw new Error("请将 DEPLOY_HOOK_URL 更新为此 Worker 的 Workers Builds Deploy Hook");
    }

    let response;
    try {
      response = await fetch(env.DEPLOY_HOOK_URL, {
        method: "POST",
        redirect: "error",
        signal: AbortSignal.timeout(20_000),
      });
    } catch {
      // 不打印 URL 或原始网络异常，避免将 Secret 写入日志。
      throw new Error("Workers Builds Deploy Hook 请求失败或超时");
    }
    if (!response.ok) {
      throw new Error(`Workers Builds Deploy Hook 返回 HTTP ${response.status}`);
    }
    let result;
    try {
      result = await response.json();
    } catch {
      throw new Error("Workers Builds Deploy Hook 未返回有效 JSON");
    }
    if (result?.success !== true || typeof result.result?.build_uuid !== "string" || !result.result.build_uuid) {
      throw new Error("Workers Builds 未确认构建已创建，请检查 Deploy Hook 配置");
    }
    console.log("Workers Builds 已触发；部署结果请查看此 Worker 的 Builds", {
      scheduledTime: new Date(controller.scheduledTime).toISOString(),
      buildId: result.result.build_uuid,
    });
  },
};
