# Telegram TRON Bot 前端

本目录是基于 Vben Admin 5.7.0 的管理前端，对接仓库根目录的 Django API。

```bash
pnpm install --frozen-lockfile
pnpm --filter @vben/web-antd dev --host 127.0.0.1
```

前端监听 `127.0.0.1:5173`，并将 `/api` 代理到 `127.0.0.1:8010`。业务页面位于 `apps/web-antd/src/views/telegram/`，API 客户端位于 `apps/web-antd/src/api/telegram.ts`。
