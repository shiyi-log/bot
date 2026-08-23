from __future__ import annotations

import asyncio
import os
import re
import unicodedata
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, Awaitable, TypeVar

from telethon import TelegramClient, errors
from telethon.sessions import StringSession

from botcore.models import BotSettings


OPERATION_TIMEOUT_SECONDS = 20.0


class TelegramAccountError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retry_after = retry_after


@dataclass(frozen=True)
class TelegramUserInfo:
    telegram_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""


@dataclass(frozen=True)
class CodeSentResult:
    phone: str
    phone_code_hash: str = field(repr=False)
    session_string: str = field(repr=False)


@dataclass(frozen=True)
class LoginResult:
    requires_password: bool
    session_string: str = field(repr=False)
    user: TelegramUserInfo | None = None


@dataclass(frozen=True)
class SessionCheckResult:
    authorized: bool
    user: TelegramUserInfo | None = None


def normalize_phone(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    normalized = re.sub(r"[\s().-]+", "", normalized)
    if normalized.startswith("00"):
        normalized = f"+{normalized[2:]}"
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", normalized):
        raise TelegramAccountError(
            "手机号必须包含国家码并使用国际格式。",
            code="invalid_phone",
        )
    return normalized


def create_telegram_client(session_string: str, api_id: int, api_hash: str) -> TelegramClient:
    return TelegramClient(
        StringSession(session_string or ""),
        api_id,
        api_hash,
        receive_updates=False,
        timeout=10,
        request_retries=2,
        connection_retries=2,
        retry_delay=1,
        flood_sleep_threshold=0,
        auto_reconnect=False,
    )


def send_login_code(phone: str) -> CodeSentResult:
    normalized_phone = normalize_phone(phone)
    client = _prepare_client("")
    return _run(_send_login_code(client, normalized_phone))


def sign_in_with_code(
    phone: str,
    code: str,
    phone_code_hash: str,
    session_string: str,
) -> LoginResult:
    normalized_phone = normalize_phone(phone)
    client = _prepare_client(session_string)
    return _run(
        _sign_in_with_code(
            client,
            normalized_phone,
            code,
            phone_code_hash,
        )
    )


def sign_in_with_password(password: str, session_string: str) -> LoginResult:
    client = _prepare_client(session_string)
    return _run(_sign_in_with_password(client, password))


def check_session(session_string: str) -> SessionCheckResult:
    client = _prepare_client(session_string)
    return _run(_check_session(client))


def _prepare_client(session_string: str) -> TelegramClient:
    _require_network_enabled()
    api_id, api_hash = _load_credentials()
    client_error: TelegramAccountError | None = None
    try:
        return create_telegram_client(session_string, api_id, api_hash)
    except TelegramAccountError as exc:
        client_error = exc
    except (TypeError, ValueError):
        client_error = TelegramAccountError(
            "Telegram 会话无效，请重新登录。",
            code="session_invalid",
        )
    client_error.__context__ = None
    client_error.__cause__ = None
    raise client_error


def _require_network_enabled() -> None:
    if os.environ.get("ENABLE_TELEGRAM_ACCOUNT_NETWORK") != "1":
        raise TelegramAccountError(
            "Telegram 账号网络访问未启用。",
            code="network_disabled",
        )


def _load_credentials() -> tuple[int, str]:
    settings = BotSettings.load()
    api_id_value = (settings.telegram_api_id or os.environ.get("TELEGRAM_API_ID", "")).strip()
    api_hash = (settings.telegram_api_hash_plain or os.environ.get("TELEGRAM_API_HASH", "")).strip()
    if not api_id_value or not api_hash:
        raise TelegramAccountError(
            "Telegram API 凭据未配置完整。",
            code="credentials_missing",
        )
    if not api_id_value.isdecimal():
        raise TelegramAccountError(
            "Telegram API ID 配置无效。",
            code="invalid_api_id",
        )
    api_id = int(api_id_value)
    if api_id <= 0:
        raise TelegramAccountError(
            "Telegram API ID 配置无效。",
            code="invalid_api_id",
        )
    return api_id, api_hash


ResultT = TypeVar("ResultT")


def _run(operation: Awaitable[ResultT]) -> ResultT:
    operation_error: TelegramAccountError | None = None
    try:
        return asyncio.run(operation)
    except TelegramAccountError as exc:
        operation_error = exc
    except Exception as exc:
        operation_error = _convert_error(exc)
    operation_error.__context__ = None
    operation_error.__cause__ = None
    raise operation_error


async def _wait(operation: Awaitable[ResultT]) -> ResultT:
    return await asyncio.wait_for(operation, timeout=OPERATION_TIMEOUT_SECONDS)


async def _disconnect(client: Any) -> None:
    with suppress(Exception):
        await _wait(client.disconnect())


async def _send_login_code(client: Any, phone: str) -> CodeSentResult:
    try:
        await _wait(client.connect())
        sent_code = await _wait(client.send_code_request(phone))
        return CodeSentResult(
            phone=phone,
            phone_code_hash=str(sent_code.phone_code_hash),
            session_string=str(client.session.save()),
        )
    finally:
        await _disconnect(client)


async def _sign_in_with_code(
    client: Any,
    phone: str,
    code: str,
    phone_code_hash: str,
) -> LoginResult:
    try:
        await _wait(client.connect())
        try:
            user = await _wait(
                client.sign_in(
                    phone=phone,
                    code=code,
                    phone_code_hash=phone_code_hash,
                )
            )
        except errors.SessionPasswordNeededError:
            return LoginResult(
                requires_password=True,
                session_string=str(client.session.save()),
            )
        return LoginResult(
            requires_password=False,
            session_string=str(client.session.save()),
            user=_user_info(user),
        )
    finally:
        await _disconnect(client)


async def _sign_in_with_password(client: Any, password: str) -> LoginResult:
    try:
        await _wait(client.connect())
        user = await _wait(client.sign_in(password=password))
        return LoginResult(
            requires_password=False,
            session_string=str(client.session.save()),
            user=_user_info(user),
        )
    finally:
        await _disconnect(client)


async def _check_session(client: Any) -> SessionCheckResult:
    try:
        await _wait(client.connect())
        authorized = await _wait(client.is_user_authorized())
        if not authorized:
            return SessionCheckResult(authorized=False)
        user = await _wait(client.get_me())
        if user is None:
            return SessionCheckResult(authorized=False)
        return SessionCheckResult(authorized=True, user=_user_info(user))
    finally:
        await _disconnect(client)


def _user_info(user: Any) -> TelegramUserInfo:
    return TelegramUserInfo(
        telegram_id=int(user.id),
        username=str(getattr(user, "username", "") or ""),
        first_name=str(getattr(user, "first_name", "") or ""),
        last_name=str(getattr(user, "last_name", "") or ""),
    )


def _convert_error(exc: Exception) -> TelegramAccountError:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return TelegramAccountError("Telegram 操作超时，请稍后重试。", code="timeout")
    if isinstance(exc, errors.PhoneCodeInvalidError):
        return TelegramAccountError("验证码错误，请重新输入。", code="invalid_code")
    if isinstance(exc, errors.PhoneCodeExpiredError):
        return TelegramAccountError("验证码已过期，请重新获取。", code="expired_code")
    if isinstance(exc, errors.SessionPasswordNeededError):
        return TelegramAccountError("该账号需要二级密码。", code="password_required")
    if isinstance(exc, errors.PasswordHashInvalidError):
        return TelegramAccountError("二级密码错误，请重新输入。", code="invalid_password")
    if isinstance(exc, errors.FloodWaitError):
        retry_after = max(0, int(getattr(exc, "seconds", 0) or 0))
        return TelegramAccountError(
            "操作过于频繁，请稍后重试。",
            code="flood_wait",
            retry_after=retry_after,
        )
    if isinstance(exc, errors.UnauthorizedError):
        return TelegramAccountError(
            "Telegram 会话已失效，请重新登录。",
            code="session_unauthorized",
        )
    if isinstance(exc, (ConnectionError, OSError)):
        return TelegramAccountError(
            "无法连接 Telegram，请稍后重试。",
            code="network_error",
        )
    return TelegramAccountError(
        "Telegram 操作失败，请稍后重试。",
        code="telegram_error",
    )
