from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BotSettingsView,
    DashboardSummaryView,
    TelegramBotButtonViewSet,
    TelegramBotViewSet,
    TelegramGroupMemberViewSet,
    TelegramGroupViewSet,
    TelegramLoginAccountViewSet,
    TelegramUserViewSet,
    TronAddressViewSet,
    TronTransferEventViewSet,
)

router = DefaultRouter()
router.register("bots", TelegramBotViewSet, basename="telegram-bot")
router.register("bot-buttons", TelegramBotButtonViewSet, basename="telegram-bot-button")
router.register("users", TelegramUserViewSet, basename="telegram-user")
router.register("groups", TelegramGroupViewSet, basename="telegram-group")
router.register("members", TelegramGroupMemberViewSet, basename="telegram-group-member")
router.register("telegram-accounts", TelegramLoginAccountViewSet, basename="telegram-login-account")
router.register("tron/addresses", TronAddressViewSet, basename="tron-address")
router.register("tron/events", TronTransferEventViewSet, basename="tron-transfer-event")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("settings/", BotSettingsView.as_view(), name="bot-settings"),
    path("", include(router.urls)),
]
