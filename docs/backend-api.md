# Backend API Contract

Base path: `/api/`. JSON is used for request and response bodies.

This starter currently uses DRF's `AllowAny` permission so a newly generated Vben frontend can be integrated immediately. A production deployment must replace it with the project's authentication and authorization policy.

## Dashboard

`GET /api/dashboard/summary/`

Returns `telegram_users`, `telegram_groups`, `telegram_bots`, `active_tron_addresses`, `total_balance_sun`, `tron_errors`, `bot_enabled`, `tron_monitor_enabled`, and `generated_at`. `bot_enabled` is true when at least one bot is enabled.

## Settings

- `GET /api/settings/`
- `PATCH /api/settings/`

Writable fields: `tron_monitor_enabled`, `tron_api_url`, `tron_api_key_env_var`, and `tron_poll_interval`. The interval must be from 5 to 3600 seconds. `tron_api_url` must use `http://` or `https://`; `tron_api_key_env_var` must be an uppercase environment variable name. The response includes read-only `tron_api_key_configured`, which only reports whether that environment variable is present. The API Key value is never accepted, stored, or returned by this API. Telegram enable and welcome settings are managed per bot.

## Telegram Bots and Buttons

- `GET /api/bots/`
- `POST /api/bots/`
- `GET /api/bots/{id}/`
- `PATCH /api/bots/{id}/`
- `DELETE /api/bots/{id}/`
- `GET /api/bot-buttons/`
- `POST /api/bot-buttons/`
- `GET /api/bot-buttons/{id}/`
- `PATCH /api/bot-buttons/{id}/`
- `DELETE /api/bot-buttons/{id}/`

Bot writable fields are `name`, `username`, `telegram_id`, `token_env_var`, `enabled`, `welcome_enabled`, and `welcome_message`. `token_env_var` is an uppercase environment variable name; the token value is never stored or returned. Responses also include read-only `credential_configured` and `button_count`. Supported welcome placeholders are `{first_name}`, `{last_name}`, `{username}`, `{user_id}`, `{group_title}`, and `{group_id}`.

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

Writable fields are `address`, `label`, and `enabled`. `address` must be a valid TRON Base58Check address. Balance, latest transaction, status, error, and check timestamps are monitor-owned read-only fields.

Filters: `enabled`, `status`. Search fields: `address`, `label`. Ordering fields: `created_at`, `updated_at`, `last_checked_at`, `balance_sun`.

## Runtime Boundaries

`python manage.py run_bot` requires `ENABLE_TELEGRAM_NETWORK=1` and at least one enabled bot whose configured `token_env_var` exists in the environment. It concurrently runs all eligible bots. Use repeatable `--bot-id ID` to select enabled bots. It persists the public user/group identity from updates, tracks first interaction per bot, records speaking membership per bot, supports `/start`, `/id`, and `/chatid`, welcomes a first private interaction, and welcomes new group members.

`python manage.py monitor_tron` requires `ENABLE_TRON_NETWORK=1`, the environment variable named by `tron_api_key_env_var`, and `tron_monitor_enabled=true`. It uses `tron_api_url` and performs read-only polling. Both commands support `--once`. Without the explicit network flag they stop with an error before making a request.
