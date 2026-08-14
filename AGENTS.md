# Telegram TRON Bot Project Rules

- Read `README.md`, `docs/backend-api.md`, and `skills/telegram-tron-bot/SKILL.md` before structural changes.
- Keep the Django backend at the repository root and Vben under `frontend/`.
- Keep local ports fixed at frontend `5173` and backend `8010` unless the user requests another change.
- Never commit `.env`, bot tokens, TRON API keys, wallet keys, Telegram sessions, or private identifiers beyond public update fields required by the app.
- Telegram and TRON network commands must remain disabled by default. Tests use fake transports/providers.
- TRON support is read-only monitoring. Do not implement signing, transfers, payment execution, or wallet authorization.
- Update backend contract docs and frontend callers together.
- Record material changes in `CHANGELOG.md` and `docs/version-record.md`.
