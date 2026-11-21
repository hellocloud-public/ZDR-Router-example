import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

let asking = false;

app.registerExtension({
  name: "ZDRRouter.Video.ApiKey",
  async afterConfigureGraph() {
    if (asking || !app.graph.nodes.some((n) => n.type === "ZDRRouterVideo")) return;
    asking = true;
    try {
      const { configured } = await (await api.fetchApi("/zdr_router/api_key")).json();
      if (configured) return;
      const key = (
        await app.extensionManager.dialog.prompt({
          title: "ZDR Router の API キー",
          message: "ZDR Router Video ノードは ZDR Router の API キーで動画を生成します。https://router.hello.ai/console/ で発行したキーを入力してください。",
        })
      )?.trim();
      if (!key) return;
      const res = await api.fetchApi("/zdr_router/api_key", { method: "POST", body: JSON.stringify({ key }) });
      app.extensionManager.toast.add({
        severity: res.ok ? "success" : "error",
        summary: res.ok ? "API キーを保存しました" : "API キーを保存できませんでした",
        life: 4000,
      });
    } finally {
      asking = false;
    }
  },
});
