# Telegram Account Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real Telethon-based Telegram client account management with a phone, code, and two-step-password login flow in the Vben admin.

**Architecture:** Keep Telegram client accounts separate from Bot API bots. A focused Django service owns Telethon calls and network gating, encrypted model fields own sensitive runtime state, DRF actions expose only public account data, and one Vben page drives the resumable three-step state machine.

**Tech Stack:** Django 5.2, Django REST Framework 3.16, Telethon, cryptography/Fernet, Vue 3, TypeScript, Ant Design Vue, Vben Admin.

---

## File Map

- Create `botcore/crypto.py`: encrypt and decrypt sensitive configuration and session strings.
- Create `botcore/services/telegram_accounts.py`: normalize phones, gate real network access, wrap Telethon operations, and translate Telegram exceptions.
- Create `botcore/tests/test_telegram_accounts.py`: deterministic unit and API tests with fake service functions.
- Create `frontend/apps/web-antd/src/views/telegram/accounts/index.vue`: account list and resumable three-step login modal.
- Modify `botcore/models.py`: add account model and Telegram API settings fields.
- Modify `botcore/serializers.py`: expose public account fields and write-only Telegram API Hash.
- Modify `botcore/views.py`: add account CRUD and login/check actions.
- Modify `botcore/urls.py`: register the account ViewSet.
- Modify `frontend/apps/web-antd/src/api/telegram.ts`: add account/config types and endpoint callers.
- Modify `frontend/apps/web-antd/src/router/routes/modules/admin.ts`: add the Telegram account menu route.
- Modify `frontend/apps/web-antd/src/views/telegram/settings/index.vue`: add Telegram API credential controls.
- Modify `.env.example`, `README.md`, `docs/backend-api.md`, `CHANGELOG.md`, `docs/version-record.md`, and `skills/telegram-tron-bot/SKILL.md`: document safe runtime use and version changes.
- Generate one Django migration containing both the account model and Telegram settings fields after model tests define the required schema.

### Task 1: Encryption And Account Schema

**Files:**
- Create: `botcore/crypto.py`
- Modify: `botcore/models.py`
- Test: `botcore/tests/test_telegram_accounts.py`
- Generate: `botcore/migrations/0008_*.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Write failing encryption and model tests**

Add tests that patch `CONFIG_ENCRYPTION_KEY`, call `encrypt_text("session-value")`, assert ciphertext differs from plaintext, and assert `decrypt_text(ciphertext)` returns the original value. Create a `TelegramLoginAccount` with raw `phone_code_hash` and `session_string`, refresh it, assert database fields do not contain the raw values, and assert the model's plain-value properties return them.

```python
@override_settings(SECRET_KEY="test-secret")
def test_login_account_encrypts_sensitive_fields(self):
    account = TelegramLoginAccount.objects.create(
        label="测试账号",
        phone="+15550001111",
        phone_code_hash="fake-code-hash",
        session_string="fake-session",
    )
    account.refresh_from_db()
    self.assertNotEqual(account.phone_code_hash, "fake-code-hash")
    self.assertNotEqual(account.session_string, "fake-session")
    self.assertEqual(account.phone_code_hash_plain, "fake-code-hash")
    self.assertEqual(account.session_string_plain, "fake-session")
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `uv run python manage.py test botcore.tests.test_telegram_accounts.TelegramAccountModelTests -v 2`

Expected: FAIL because `botcore.crypto` and `TelegramLoginAccount` do not exist.

- [ ] **Step 3: Add dependencies and minimal encryption implementation**

Add `cryptography>=46,<47` and `telethon>=1.43,<2` with `uv add`. Implement Fernet key derivation from `CONFIG_ENCRYPTION_KEY` or `settings.SECRET_KEY`, plus strict decrypt behavior that returns an empty string for an invalid Fernet token and never logs ciphertext.

```python
def _build_key() -> bytes:
    raw = os.getenv("CONFIG_ENCRYPTION_KEY") or settings.SECRET_KEY
    return base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
```

- [ ] **Step 4: Add the account model**

Define status choices `pending`, `code_sent`, `password_required`, `logged_in`, `session_expired`, and `error`. Encrypt `phone_code_hash` and `session_string` before save, add plain-value properties, use `BigIntegerField` for `telegram_id`, and order by newest update. In the same schema change, add `telegram_api_id` and encrypted `telegram_api_hash` fields to `BotSettings`.

- [ ] **Step 5: Generate migration and verify GREEN**

Run:

```bash
uv run python manage.py makemigrations botcore
uv run python manage.py test botcore.tests.test_telegram_accounts.TelegramAccountModelTests -v 2
```

Expected: migration created after `0007`; model tests PASS.

- [ ] **Step 6: Commit schema work**

```bash
git add pyproject.toml uv.lock botcore/crypto.py botcore/models.py botcore/migrations botcore/tests/test_telegram_accounts.py
git commit -m "feat: add encrypted Telegram login accounts"
```

### Task 2: Telegram Account Login Service

**Files:**
- Create: `botcore/services/telegram_accounts.py`
- Test: `botcore/tests/test_telegram_accounts.py`

- [ ] **Step 1: Write failing service tests**

Cover international phone normalization, network disabled, missing API credentials, successful code send, code login without password, code login requiring password, password completion, session validation, timeout, invalid code, expired code, invalid password, and flood wait. Patch the Telethon client factory with an async fake; never instantiate a real network client.

```python
def test_normalize_phone_requires_country_code(self):
    self.assertEqual(normalize_phone("00 86 138-0013-8000"), "+8613800138000")
    with self.assertRaisesMessage(TelegramAccountError, "国际格式"):
        normalize_phone("13800138000")
```

- [ ] **Step 2: Run service tests and verify RED**

Run: `uv run python manage.py test botcore.tests.test_telegram_accounts.TelegramAccountServiceTests -v 2`

Expected: FAIL because the service module does not exist.

- [ ] **Step 3: Implement network gate and credentials**

Require `ENABLE_TELEGRAM_ACCOUNT_NETWORK=1`. Resolve API ID and decrypted API Hash from `BotSettings`, falling back to `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`. Reject a missing or non-numeric ID before client creation.

- [ ] **Step 4: Implement bounded Telethon operations**

Implement `send_login_code`, `sign_in_with_code`, `sign_in_with_password`, and `check_session` with `asyncio.wait_for`, `StringSession`, `receive_updates=False`, and guaranteed disconnect in `finally`. Return small dataclasses or dictionaries containing only the session and public `get_me()` result needed by the caller.

- [ ] **Step 5: Implement stable exception translation**

Map Telethon errors to Chinese messages without including submitted secrets: invalid/expired code, password required/invalid, flood wait, timeout, and unauthorized session. Preserve retryable login state in the caller.

- [ ] **Step 6: Run service tests and verify GREEN**

Run: `uv run python manage.py test botcore.tests.test_telegram_accounts.TelegramAccountServiceTests -v 2`

Expected: PASS with no network traffic.

- [ ] **Step 7: Commit the service**

```bash
git add botcore/services/telegram_accounts.py botcore/tests/test_telegram_accounts.py
git commit -m "feat: implement Telegram account login service"
```

### Task 3: Settings And Account API

**Files:**
- Modify: `botcore/models.py`
- Modify: `botcore/serializers.py`
- Modify: `botcore/views.py`
- Modify: `botcore/urls.py`
- Modify: `botcore/tests/test_api.py`
- Modify: `botcore/tests/test_telegram_accounts.py`

- [ ] **Step 1: Write failing settings contract tests**

PATCH `/api/settings/` with `telegram_api_id` and `telegram_api_hash`; assert the ID is returned, raw Hash is absent, `telegram_api_hash_configured` is true, and preview is masked. Assert environment fallback is reported without returning the environment value.

- [ ] **Step 2: Write failing account API tests**

Test paginated list, start, code, password, continue-state responses, status check, and delete. Patch service functions with deterministic fakes. Assert every serialized response excludes `phone_code_hash`, `session_string`, raw API Hash, code, and password.

- [ ] **Step 3: Run API tests and verify RED**

Run:

```bash
uv run python manage.py test botcore.tests.test_api.BotSettingsApiTests botcore.tests.test_telegram_accounts.TelegramAccountApiTests -v 2
```

Expected: FAIL because settings fields and routes are missing.

- [ ] **Step 4: Implement Telegram settings contract**

Use the `telegram_api_hash` and `telegram_api_id` fields added to `BotSettings` in Task 1. Make Hash write-only in `BotSettingsSerializer`; expose `telegram_api_hash_configured` and a masked preview. Preserve an existing encrypted Hash when PATCH omits the write-only field.

- [ ] **Step 5: Implement account serializer and ViewSet**

Expose public identity, state, `has_session`, safe error summary, and timestamps. Implement custom `login_start`, `login_code`, `login_password`, and `check` actions. Validate state transitions and update encrypted fields atomically. Use HTTP 503 for disabled network/configuration and HTTP 400 for invalid login input.

- [ ] **Step 6: Run API tests and verify GREEN**

Run the command from Step 3.

Expected: PASS; response secrecy assertions PASS.

- [ ] **Step 7: Commit the API**

```bash
git add botcore/models.py botcore/serializers.py botcore/views.py botcore/urls.py botcore/migrations botcore/tests/test_api.py botcore/tests/test_telegram_accounts.py
git commit -m "feat: expose Telegram account login API"
```

### Task 4: Vben Account Page And Settings

**Files:**
- Modify: `frontend/apps/web-antd/src/api/telegram.ts`
- Modify: `frontend/apps/web-antd/src/router/routes/modules/admin.ts`
- Create: `frontend/apps/web-antd/src/views/telegram/accounts/index.vue`
- Modify: `frontend/apps/web-antd/src/views/telegram/settings/index.vue`

- [ ] **Step 1: Add exact frontend API types and callers**

Define `TelegramLoginAccount`, `TelegramLoginStartResult`, `TelegramLoginCodeResult`, settings Hash status fields, and functions for list/delete/start/code/password/check. Match trailing-slash DRF routes exactly and set login request timeouts to 180 seconds.

- [ ] **Step 2: Run typecheck and verify RED**

Run: `cd frontend && pnpm --filter @vben/web-antd typecheck`

Expected: FAIL while the new page references types and functions not yet present or incomplete.

- [ ] **Step 3: Implement the account table**

Add credentials status, login and refresh controls, searchable paginated table, status tags, public identity columns, last-check time, and row actions. Use deletion confirmation text that states only local data is removed.

- [ ] **Step 4: Implement the resumable three-step modal**

Use Ant Design `Steps`, international phone input, code input with resend, password input with visibility disabled, duplicate-submit protection, and Chinese errors. Open `code_sent` at step 2 and `password_required` at step 3; other abnormal states restart from phone.

- [ ] **Step 5: Add menu route and settings controls**

Add `/admin/telegram-accounts` titled “Telegram 账号”. In settings, add API ID and write-only API Hash inputs, configured tag, masked preview, and a warning that real login requires the environment network switch.

- [ ] **Step 6: Run frontend checks and verify GREEN**

Run:

```bash
cd frontend
pnpm --filter @vben/web-antd typecheck
pnpm --filter @vben/web-antd build
```

Expected: both commands exit 0.

- [ ] **Step 7: Commit frontend work**

```bash
git add frontend/apps/web-antd/src/api/telegram.ts frontend/apps/web-antd/src/router/routes/modules/admin.ts frontend/apps/web-antd/src/views/telegram/accounts/index.vue frontend/apps/web-antd/src/views/telegram/settings/index.vue
git commit -m "feat: add Telegram account management UI"
```

### Task 5: Documentation And Project Skill

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/backend-api.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/version-record.md`
- Modify: `skills/telegram-tron-bot/SKILL.md`

- [ ] **Step 1: Document environment and API contract**

Add `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `CONFIG_ENCRYPTION_KEY`, and `ENABLE_TELEGRAM_ACCOUNT_NETWORK=0` examples with blank secret values. Document account routes, state transitions, response secrecy, deletion semantics, and default-disabled real network behavior.

- [ ] **Step 2: Update user-facing and durable version records**

Record the Telegram account page, three-step login, encrypted session storage, settings fields, fake-client test boundary, and the fact that no personal-account listener or sender is included. Promote the combined clone and account-management release to `0.4.0` dated 2026-08-23.

- [ ] **Step 3: Update the project-local skill**

Add account-login workflow constraints: require the dedicated network switch, encrypt sessions, use fake clients in tests, never return secrets, and distinguish client accounts from Bot API bots.

- [ ] **Step 4: Validate the skill and docs**

Run:

```bash
python /Users/a399/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/telegram-tron-bot
git diff --check
```

Expected: skill validation succeeds and no whitespace errors are reported.

- [ ] **Step 5: Commit documentation**

```bash
git add .env.example README.md docs/backend-api.md CHANGELOG.md docs/version-record.md skills/telegram-tron-bot/SKILL.md
git commit -m "docs: record Telegram account management"
```

### Task 6: Full Verification And Publication

**Files:**
- Verify all changed files; do not add `docs/screenshots/`.

- [ ] **Step 1: Run complete backend verification**

```bash
uv run python manage.py test botcore.tests -v 1
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

Expected: all tests PASS, system check reports no issues, and no migration changes are detected.

- [ ] **Step 2: Run complete frontend verification**

```bash
cd frontend
pnpm --filter @vben/web-antd typecheck
pnpm --filter @vben/web-antd build
```

Expected: both commands exit 0.

- [ ] **Step 3: Inspect release diff and secret safety**

Run `git status --short`, `git diff --check`, and targeted searches for session literals, API Hash values, codes, passwords, and token values. Confirm `docs/screenshots/` remains untracked and unstaged.

- [ ] **Step 4: Commit any final integration-only fixes**

```bash
git add .env.example CHANGELOG.md README.md botcore config docs/backend-api.md docs/version-record.md frontend/apps/web-antd/src skills/telegram-tron-bot pyproject.toml uv.lock
git commit -m "chore: finalize Telegram bot template v0.4.0"
```

Skip this commit if the worktree is already clean apart from `docs/screenshots/`.

- [ ] **Step 5: Push the verified branch**

Run: `git push origin main`

Expected: `origin/main` advances to the final verified commit. Do not push if any verification step fails.
