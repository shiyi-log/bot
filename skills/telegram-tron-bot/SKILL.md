---
name: telegram-tron-bot
description: Maintain and extend this Django, Vben, Telegram Bot API, and TRON address monitoring starter. Use when working in the telegram-tron-bot-template repository on bot welcome messages, Telegram user, group, or speaking-member identity capture, TRON read-only monitoring, Django REST APIs, Vben admin pages, runtime commands, tests, or version records.
---

# Telegram TRON Bot

Work from the repository root. Keep Django at the root and Vben under `frontend/`.

## Workflow

1. Read `README.md`, `docs/backend-api.md`, `CHANGELOG.md`, and `git status --short` before editing.
2. Preserve the API contract. Update backend serializers, `docs/backend-api.md`, frontend types, and callers together when a contract changes.
3. Keep Telegram and TRON network access fail-closed. Unit tests must use fake transports/providers. Store only each bot's token environment variable name in the database; never put bot tokens or TRON API keys in source, logs, fixtures, API responses, or commits.
4. Treat Telegram IDs as 64-bit values. Persist only public update fields needed by the application.
5. Create or refresh group membership only from normal content messages in groups and supergroups. Do not infer membership from join/service updates, private chats, channels, or anonymous `sender_chat` messages.
6. Keep TRON polling read-only. Do not add signing, transfers, private keys, wallet authorization, or payment execution to this starter.
   Resource monitoring may persist Energy/Bandwidth baselines and change alerts. The block scanner may parse successful standard TRC20 `approve` calls and `AccountPermissionUpdateContract` values into a read-only alert feed, but it must never submit either operation.
7. Use `[IP]:8010` for Django and `[IP]:5173` for Vben development so this project does not collide with neighboring workspaces.
8. Add focused backend tests for bot/runtime changes. Run frontend typecheck and build for UI/API changes.
9. Record user-visible changes in `CHANGELOG.md` and `docs/version-record.md`.
10. Keep Telegram client-account login separate from Bot API bot polling. Use Telethon only behind `ENABLE_TELEGRAM_ACCOUNT_NETWORK=1`; encrypt API Hash, phone-code hash, and StringSession with the project encryption helper, and never return or log them.

## Commands

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver [IP]:8010
uv run python manage.py test botcore.tests
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm --filter @vben/web-antd dev --host [IP]
pnpm --filter @vben/web-antd typecheck
pnpm --filter @vben/web-antd build
```

## Runtime Boundaries

- Start Telegram polling only with `ENABLE_TELEGRAM_NETWORK=1` and an enabled bot whose configured token environment variable is present.
- Start personal Telegram account login only with `ENABLE_TELEGRAM_ACCOUNT_NETWORK=1` and valid API ID/API Hash; tests must use fake Telethon clients.
- Keep account login state resumable across `code_sent` and `password_required`, but do not run session checks against those temporary states.
- Keep welcome messages and URL inline buttons scoped per bot. Attach buttons only to `/start` and welcome messages.
- Start TRON polling only with `ENABLE_TRON_NETWORK=1`, a configured API key, and `tron_monitor_enabled=true`.
- Treat the first resource snapshot as a silent baseline. Keep chain alerts idempotent and expose them through the read-only `/api/tron/alerts/` contract. No Telegram alert recipient is configured by default.
- Distinguish fake/local validation from real Telegram or TRON verification in every report.
- Replace DRF `AllowAny` before any production deployment.
