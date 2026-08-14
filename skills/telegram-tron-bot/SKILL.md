---
name: telegram-tron-bot
description: Maintain and extend this Django, Vben, Telegram Bot API, and TRON address monitoring starter. Use when working in the telegram-tron-bot-template repository on bot welcome messages, Telegram user or group identity capture, TRON read-only monitoring, Django REST APIs, Vben admin pages, runtime commands, tests, or version records.
---

# Telegram TRON Bot

Work from the repository root. Keep Django at the root and Vben under `frontend/`.

## Workflow

1. Read `README.md`, `docs/backend-api.md`, `CHANGELOG.md`, and `git status --short` before editing.
2. Preserve the API contract. Update backend serializers, `docs/backend-api.md`, frontend types, and callers together when a contract changes.
3. Keep Telegram and TRON network access fail-closed. Unit tests must use fake transports/providers. Never put bot tokens or TRON API keys in source, logs, fixtures, or commits.
4. Treat Telegram IDs as 64-bit values. Persist only public update fields needed by the application.
5. Keep TRON polling read-only. Do not add signing, transfers, private keys, wallet authorization, or payment execution to this starter.
6. Use `127.0.0.1:8010` for Django and `127.0.0.1:5173` for Vben development so this project does not collide with neighboring workspaces.
7. Add focused backend tests for bot/runtime changes. Run frontend typecheck and build for UI/API changes.
8. Record user-visible changes in `CHANGELOG.md` and `docs/version-record.md`.

## Commands

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8010
uv run python manage.py test botcore.tests
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm --filter @vben/web-antd dev --host 127.0.0.1
pnpm --filter @vben/web-antd typecheck
pnpm --filter @vben/web-antd build
```

## Runtime Boundaries

- Start Telegram polling only with `ENABLE_TELEGRAM_NETWORK=1`, a configured token, and `bot_enabled=true`.
- Start TRON polling only with `ENABLE_TRON_NETWORK=1`, a configured API key, and `tron_monitor_enabled=true`.
- Distinguish fake/local validation from real Telegram or TRON verification in every report.
- Replace DRF `AllowAny` before any production deployment.
