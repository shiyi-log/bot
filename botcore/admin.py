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
])
