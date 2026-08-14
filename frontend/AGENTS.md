# Vben Frontend Rules

- Read the root `AGENTS.md`, `README.md`, and `docs/backend-api.md` before API or routing changes.
- Keep app-specific code in `apps/web-antd/src/api/telegram.ts`, `router/routes/modules/admin.ts`, and `views/telegram/`.
- Use the existing Vben and Ant Design Vue components and established request client.
- Keep development port `5173` and proxy `/api` to `127.0.0.1:8010`.
- Run the web-antd typecheck and build after frontend changes.
