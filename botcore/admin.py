from django.contrib import admin

from .models import (
    BotSettings,
    TelegramBot,
    TelegramBotButton,
    TelegramBotUser,
    TelegramGroup,
    TelegramGroupMember,
    TelegramUser,
    TronAddress,
    TronAlert,
    TronBlockCursor,
    TronTransferEvent,
)

admin.site.register([
    TelegramBot,
    TelegramBotButton,
    TelegramBotUser,
    TelegramUser,
    TelegramGroup,
    TelegramGroupMember,
    BotSettings,
    TronAddress,
    TronAlert,
    TronBlockCursor,
    TronTransferEvent,
])
