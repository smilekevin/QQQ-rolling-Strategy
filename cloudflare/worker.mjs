// 定时触发 Pages 构建；行情下载与回测由 Pages 构建环境执行。
export default {
  async scheduled(controller, env) {
    if (!env.DEPLOY_HOOK_URL) {
      throw new Error("请先配置 DEPLOY_HOOK_URL Secret");
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
      throw new Error("Pages Deploy Hook 请求失败或超时");
    }
    if (!response.ok) {
      throw new Error(`Pages Deploy Hook 返回 HTTP ${response.status}`);
    }
    console.log("Pages 构建已触发；构建结果请查看 Pages Deployments", {
      scheduledTime: new Date(controller.scheduledTime).toISOString(),
      status: response.status,
    });
  },
};
