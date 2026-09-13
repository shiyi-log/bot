# Backend API Contract

Base path: `/api/`. JSON is used for request and response bodies.

This starter currently uses DRF's `AllowAny` permission so a newly generated Vben frontend can be integrated immediately. A production deployment must replace it with the project's authentication and authorization policy.

## Dashboard

`GET /api/dashboard/summary/`

Returns `telegram_users`, `telegram_groups`, `telegram_bots`, `active_tron_addresses`, `total_balance_sun`, `tron_errors`, `bot_enabled`, `tron_monitor_enabled`, and `generated_at`. `bot_enabled` is true when at least one bot is enabled.

## Settings

- `GET /api/settings/`
- `PATCH /api/settings/`

Writable fields: `telegram_api_id`, `telegram_api_hash`, `tron_monitor_enabled`, `tron_api_url`, `tron_api_key_env_var`, `tron_api_key`, and `tron_poll_interval`. Telegram API Hash and TRON API Key are write-only; responses return only configured flags and masked previews. Telegram API ID and Hash use database values first and `TELEGRAM_API_ID`/`TELEGRAM_API_HASH` as fallbacks. Telegram Hash is encrypted with the project Fernet helper; the TRON key remains plain text by explicit project policy. Telegram account login also requires `ENABLE_TELEGRAM_ACCOUNT_NETWORK=1`.

## Telegram Client Accounts

- `GET /api/telegram-accounts/`
- `GET /api/telegram-accounts/{id}/`
- `DELETE /api/telegram-accounts/{id}/`
- `POST /api/telegram-accounts/login/start/`
- `POST /api/telegram-accounts/login/code/`
- `POST /api/telegram-accounts/login/password/`
- `POST /api/telegram-accounts/{id}/check/`

The account collection is read-only: generic `POST`, `PUT`, and `PATCH` return `405`. List queries use standard `page`, `page_size`, and `search`; search covers `phone`, `telegram_id`, `username`, `first_name`, `last_name`, and `label`. Login states are `pending`, `code_sent`, `password_required`, `logged_in`, `session_expired`, and `error`. Temporary `code_sent` and `password_required` accounts can be resumed, but only `logged_in` sessions can be checked. Login requests accept an international phone number and never return API Hash, phone-code hash, password, or StringSession. Real Telegram access is fail-closed until `ENABLE_TELEGRAM_ACCOUNT_NETWORK=1`; tests use fake Telethon clients.

## Telegram Bots and Buttons

- `GET /api/bots/`
- `POST /api/bots/`
- `GET /api/bots/{id}/`
- `PATCH /api/bots/{id}/`
- `DELETE /api/bots/{id}/`
- `POST /api/bots/{id}/clone/`
- `GET /api/bot-buttons/`
- `POST /api/bot-buttons/`
- `GET /api/bot-buttons/{id}/`
- `PATCH /api/bot-buttons/{id}/`
- `DELETE /api/bot-buttons/{id}/`

Bot writable fields are `name`, `username`, `telegram_id`, `token_env_var`, `enabled`, `welcome_enabled`, `welcome_message`, and `clone_enabled`. `token_env_var` is an uppercase environment variable name; the token value is never stored or returned. Responses also include read-only `credential_configured`, `button_count`, `clone_count`, and `cloned_from`. Supported welcome placeholders are `{first_name}`, `{last_name}`, `{username}`, `{user_id}`, `{group_title}`, and `{group_id}`.

The clone endpoint requires `clone_enabled=true` and copies the welcome configuration and URL buttons into a new disabled bot. It never copies the Telegram ID, username, token environment variable, or token value; a unique token environment variable name is generated unless one is supplied. The optional `billing_plan` field is reserved for future paid cloning. The response includes `billing.status=reserved` and `billing.provider=billing-not-configured`; no payment is executed by this template.

Button writable fields are `bot`, `text`, `url`, `row`, `position`, and `enabled`. Buttons are URL-only Telegram inline keyboard buttons. Enabled buttons are grouped by row and ordered by position, and are attached only to `/start`, first-private-interaction welcomes, and new-member welcomes. Bot filters: `enabled`. Button filters: `bot`, `enabled`.

## Telegram Users and Groups

- `GET /api/users/`
- `GET /api/users/{id}/`
- `GET /api/groups/`
- `GET /api/groups/{id}/`
- `GET /api/members/`
- `GET /api/members/{id}/`

List responses use `{count, next, previous, results}`. Use `page` and `page_size` (maximum 100) for pagination and `search` for text search.

User filters: `is_active`, `is_bot`, `language_code`. User ordering fields: `telegram_id`, `first_seen_at`, `last_seen_at`, `message_count`.

Group filters: `is_active`, `group_type`. Group ordering fields: `telegram_id`, `first_seen_at`, `last_seen_at`, `message_count`.

Group responses include `member_count`, which counts distinct users who have spoken in that group. Member records are scoped to the receiving bot and are created or refreshed only from normal content messages in a group or supergroup. Joining alone, private chats, channel posts, service-only updates, and anonymous `sender_chat` messages do not create membership records. Username and name snapshots update on the member's next qualifying group message.

Member responses include `bot` and `bot_name`. Member filters: `bot`, `group`, `group__telegram_id`, `user`, and `user__telegram_id`. Member ordering fields: `first_spoke_at`, `last_spoke_at`, and `message_count`. Search covers group ID/title, Telegram user ID, username, first name, and last name.

## TRON Addresses

- `GET /api/tron/addresses/`
- `POST /api/tron/addresses/`
- `GET /api/tron/addresses/{id}/`
- `PATCH /api/tron/addresses/{id}/`
- `DELETE /api/tron/addresses/{id}/`
- `POST /api/tron/addresses/{id}/check/`

Writable fields are `address`, `label`, and `enabled`. `address` must be a valid TRON Base58Check address. Balance, USDT balance, latest transaction, status, error, and check timestamps are monitor-owned read-only fields. `usdt_balance_sun` stores TRC20 USDT in its 6-decimal smallest unit. The `check` action performs one read-only account snapshot and requires `ENABLE_TRON_NETWORK=1` plus a configured key.

Filters: `enabled`, `status`. Search fields: `address`, `label`. Ordering fields: `created_at`, `updated_at`, `last_checked_at`, `balance_sun`.

## Runtime Boundaries

`GET /api/tron/events/` provides a read-only paginated view of scanner events. It supports `currency`, `block_number`, `from_address`, `to_address`, and search by transaction/address.

`python manage.py run_bot` requires `ENABLE_TELEGRAM_NETWORK=1` and at least one enabled bot whose configured `token_env_var` exists in the environment. It concurrently runs all eligible bots. Use repeatable `--bot-id ID` to select enabled bots. It persists the public user/group identity from updates, tracks first interaction per bot, records speaking membership per bot, supports `/start`, `/id`, and `/chatid`, welcomes a first private interaction, and welcomes new group members.

`python manage.py monitor_tron` requires `ENABLE_TRON_NETWORK=1`, a configured database Key or the environment variable named by `tron_api_key_env_var`, and `tron_monitor_enabled=true`. It uses `tron_api_url`, performs read-only polling, rotates multiple keys, and retries the next key on HTTP 401. Both commands support `--once`. Without the explicit network flag they stop with an error before making a request.

`python manage.py scan_tron_blocks` is an independent read-only scanner. It requires `ENABLE_TRON_NETWORK=1` and the same API key configuration, keeps a `TronBlockCursor`, scans confirmed blocks (`--confirmations`, default 20), and stores only TRX/TRC20 USDT transfer events matching enabled monitored addresses in `TronTransferEvent`. It is idempotent by `tx_id` and `event_index`, supports bounded `--batch-size`, and performs no signing, transfer, payment, or notification action.
