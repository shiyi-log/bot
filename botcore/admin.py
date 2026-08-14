from django.contrib import admin

from .models import BotSettings, TelegramGroup, TelegramUser, TronAddress

admin.site.register([TelegramUser, TelegramGroup, BotSettings, TronAddress])
