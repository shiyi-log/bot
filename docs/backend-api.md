# Backend API Contract

Base path: `/api/`. JSON is used for request and response bodies.

This starter currently uses DRF's `AllowAny` permission so a newly generated Vben frontend can be integrated immediately. A production deployment must replace it with the project's authentication and authorization policy.

## Dashboard

`GET /api/dashboard/summary/`

Returns `telegram_users`, `telegram_groups`, `active_tron_addresses`, `total_balance_sun`, `tron_errors`, `bot_enabled`, `tron_monitor_enabled`, and `generated_at`.

## Settings

- `GET /api/settings/`
- `PATCH /api/settings/`

Writable fields: `bot_enabled`, `welcome_enabled`, `welcome_message`, `tron_monitor_enabled`, and `tron_poll_interval`. The interval must be from 5 to 3600 seconds. Supported welcome placeholders are `{first_name}`, `{last_name}`, `{username}`, `{user_id}`, `{group_title}`, and `{group_id}`.

## Telegram Users and Groups

- `GET /api/users/`
- `GET /api/users/{id}/`
- `GET /api/groups/`
- `GET /api/groups/{id}/`

List responses use `{count, next, previous, results}`. Use `page` and `page_size` (maximum 100) for pagination and `search` for text search.

User filters: `is_active`, `is_bot`, `language_code`. User ordering fields: `telegram_id`, `first_seen_at`, `last_seen_at`, `message_count`.

Group filters: `is_active`, `group_type`. Group ordering fields: `telegram_id`, `first_seen_at`, `last_seen_at`, `message_count`.

## TRON Addresses

- `GET /api/tron/addresses/`
- `POST /api/tron/addresses/`
- `GET /api/tron/addresses/{id}/`
- `PATCH /api/tron/addresses/{id}/`
- `DELETE /api/tron/addresses/{id}/`

Writable fields are `address`, `label`, and `enabled`. `address` must be a valid TRON Base58Check address. Balance, latest transaction, status, error, and check timestamps are monitor-owned read-only fields.

Filters: `enabled`, `status`. Search fields: `address`, `label`. Ordering fields: `created_at`, `updated_at`, `last_checked_at`, `balance_sun`.

## Runtime Boundaries

`python manage.py run_bot` requires `ENABLE_TELEGRAM_NETWORK=1`, `TELEGRAM_BOT_TOKEN`, and `bot_enabled=true`. It persists the public user/group identity from updates, supports `/start`, `/id`, and `/chatid`, welcomes a first private interaction, and welcomes new group members.

`python manage.py monitor_tron` requires `ENABLE_TRON_NETWORK=1`, `TRONGRID_API_KEY`, and `tron_monitor_enabled=true`. It performs read-only polling. Both commands support `--once`. Without the explicit network flag they stop with an error before making a request.
