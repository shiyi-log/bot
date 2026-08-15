from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BotSettingsView,
    DashboardSummaryView,
    TelegramGroupMemberViewSet,
    TelegramGroupViewSet,
    TelegramUserViewSet,
    TronAddressViewSet,
)

router = DefaultRouter()
router.register("users", TelegramUserViewSet, basename="telegram-user")
router.register("groups", TelegramGroupViewSet, basename="telegram-group")
router.register("members", TelegramGroupMemberViewSet, basename="telegram-group-member")
router.register("tron/addresses", TronAddressViewSet, basename="tron-address")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("settings/", BotSettingsView.as_view(), name="bot-settings"),
    path("", include(router.urls)),
]
