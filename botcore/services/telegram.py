from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from django.db.models import F

from botcore.models import BotSettings, TelegramGroup, TelegramGroupMember, TelegramUser


MEMBER_MESSAGE_FIELDS = {
    "animation", "audio", "caption", "contact", "dice", "document", "game",
    "location", "photo", "poll", "sticker", "story", "text", "venue", "video",
    "video_note", "voice",
}


class TelegramTransport(Protocol):
    def send_message(self, chat_id: int, text: str) -> None: ...

    def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]: ...


class TelegramBotAPITransport:
    def __init__(self, token: str, api_base: str = "https://api.telegram.org"):
        self.base_url = f"{api_base.rstrip('/')}/bot{token}"

    def _request(self, method: str, payload: dict[str, Any]) -> Any:
        data = urllib.parse.urlencode(payload).encode()
        with urllib.request.urlopen(f"{self.base_url}/{method}", data=data, timeout=60) as response:
            body = json.load(response)
        if not body.get("ok"):
            raise RuntimeError(f"Telegram API request failed: {method}")
        return body.get("result")

    def send_message(self, chat_id: int, text: str) -> None:
        self._request("sendMessage", {"chat_id": chat_id, "text": text})

    def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            payload["offset"] = offset
        return self._request("getUpdates", payload) or []


@dataclass(frozen=True)
class UpdateResult:
    user_id: int | None = None
    group_id: int | None = None
    replies_sent: int = 0


def _persist_user(data: dict[str, Any]) -> tuple[TelegramUser, bool]:
    telegram_id = int(data["id"])
    defaults = {
        "username": data.get("username", ""),
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "language_code": data.get("language_code", ""),
        "is_bot": bool(data.get("is_bot", False)),
        "is_active": True,
    }
    user, created = TelegramUser.objects.update_or_create(telegram_id=telegram_id, defaults=defaults)
    TelegramUser.objects.filter(pk=user.pk).update(message_count=F("message_count") + 1)
    user.refresh_from_db()
    return user, created


def _persist_group(chat: dict[str, Any]) -> TelegramGroup | None:
    chat_type = chat.get("type")
    if chat_type not in {"group", "supergroup", "channel"}:
        return None
    group, _ = TelegramGroup.objects.update_or_create(
        telegram_id=int(chat["id"]),
        defaults={
            "title": chat.get("title", ""),
            "username": chat.get("username", ""),
            "group_type": chat_type,
            "is_active": True,
        },
    )
    TelegramGroup.objects.filter(pk=group.pk).update(message_count=F("message_count") + 1)
    group.refresh_from_db()
    return group


def _persist_group_member(
    message: dict[str, Any],
    group: TelegramGroup | None,
    user: TelegramUser,
    sender: dict[str, Any],
) -> TelegramGroupMember | None:
    if not group or group.group_type not in {TelegramGroup.GroupType.GROUP, TelegramGroup.GroupType.SUPERGROUP}:
        return None
    if message.get("sender_chat") or not MEMBER_MESSAGE_FIELDS.intersection(message):
        return None

    member, _ = TelegramGroupMember.objects.update_or_create(
        group=group,
        user=user,
        defaults={
            "username": sender.get("username", ""),
            "first_name": sender.get("first_name", ""),
            "last_name": sender.get("last_name", ""),
        },
    )
    TelegramGroupMember.objects.filter(pk=member.pk).update(message_count=F("message_count") + 1)
    member.refresh_from_db()
    return member


def _render_welcome(template: str, user: dict[str, Any], chat: dict[str, Any]) -> str:
    values = {
        "first_name": user.get("first_name", "") or user.get("username", "") or str(user.get("id", "")),
        "last_name": user.get("last_name", ""),
        "username": user.get("username", ""),
        "user_id": user.get("id", ""),
        "group_title": chat.get("title", ""),
        "group_id": chat.get("id", ""),
    }
    try:
        return template.format_map(values)
    except (KeyError, ValueError):
        return template


def handle_update(update: dict[str, Any], transport: TelegramTransport) -> UpdateResult:
    """Persist the public identity boundary and send deterministic bot replies."""
    message = update.get("message") or {}
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    if not sender.get("id") or not chat.get("id"):
        return UpdateResult()

    user, first_interaction = _persist_user(sender)
    group = _persist_group(chat)
    _persist_group_member(message, group, user, sender)
    settings = BotSettings.load()
    replies = 0
    text = (message.get("text") or "").split("@", 1)[0].strip().lower()

    if text == "/start":
        transport.send_message(int(chat["id"]), _render_welcome(settings.welcome_message, sender, chat))
        replies += 1
    elif text == "/id":
        transport.send_message(int(chat["id"]), f"用户 ID: {user.telegram_id}")
        replies += 1
    elif text == "/chatid":
        transport.send_message(int(chat["id"]), f"群组 ID: {chat['id']}")
        replies += 1

    welcome_users = message.get("new_chat_members") or []
    if settings.welcome_enabled:
        if group and welcome_users:
            for member in welcome_users:
                if member.get("is_bot"):
                    continue
                _persist_user(member)
                transport.send_message(int(chat["id"]), _render_welcome(settings.welcome_message, member, chat))
                replies += 1
        elif chat.get("type") == "private" and first_interaction and not text.startswith("/"):
            transport.send_message(int(chat["id"]), _render_welcome(settings.welcome_message, sender, chat))
            replies += 1

    return UpdateResult(user_id=user.telegram_id, group_id=group.telegram_id if group else None, replies_sent=replies)
