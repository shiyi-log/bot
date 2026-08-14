# Telegram TRON Bot Frontend

Vben Admin 5.7.0 frontend for the repository root Django API.

```bash
pnpm install --frozen-lockfile
pnpm --filter @vben/web-antd dev --host 127.0.0.1
```

The app listens on `127.0.0.1:5173` and proxies `/api` to `127.0.0.1:8010`.

Application code is under `apps/web-antd/src/views/telegram/` and the API client is `apps/web-antd/src/api/telegram.ts`.
