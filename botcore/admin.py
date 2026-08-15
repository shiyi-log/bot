from django.contrib import admin

from .models import BotSettings, TelegramGroup, TelegramGroupMember, TelegramUser, TronAddress

admin.site.register([TelegramUser, TelegramGroup, TelegramGroupMember, BotSettings, TronAddress])
