from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import generics, viewsets
from rest_framework.response import Response

from .models import BotSettings, TelegramGroup, TelegramGroupMember, TelegramUser, TronAddress
from .serializers import (
    BotSettingsSerializer,
    TelegramGroupSerializer,
    TelegramGroupMemberSerializer,
    TelegramUserSerializer,
    TronAddressSerializer,
)


class DashboardSummaryView(generics.GenericAPIView):
    pagination_class = None

    def get(self, request):
        settings = BotSettings.load()
        return Response({
            "telegram_users": TelegramUser.objects.count(),
            "telegram_groups": TelegramGroup.objects.count(),
            "active_tron_addresses": TronAddress.objects.filter(enabled=True).count(),
            "total_balance_sun": TronAddress.objects.filter(enabled=True).aggregate(total=Sum("balance_sun"))["total"] or 0,
            "tron_errors": TronAddress.objects.filter(enabled=True, status=TronAddress.Status.ERROR).count(),
            "bot_enabled": settings.bot_enabled,
            "tron_monitor_enabled": settings.tron_monitor_enabled,
            "generated_at": timezone.now(),
        })


class BotSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = BotSettingsSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return BotSettings.load()


class TelegramUserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TelegramUser.objects.all()
    serializer_class = TelegramUserSerializer
    filterset_fields = ["is_active", "is_bot", "language_code"]
    search_fields = ["telegram_id", "username", "first_name", "last_name"]
    ordering_fields = ["telegram_id", "first_seen_at", "last_seen_at", "message_count"]


class TelegramGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TelegramGroup.objects.annotate(member_count=Count("members")).order_by("-last_seen_at")
    serializer_class = TelegramGroupSerializer
    filterset_fields = ["is_active", "group_type"]
    search_fields = ["telegram_id", "title", "username"]
    ordering_fields = ["telegram_id", "first_seen_at", "last_seen_at", "message_count"]


class TelegramGroupMemberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TelegramGroupMember.objects.select_related("group", "user")
    serializer_class = TelegramGroupMemberSerializer
    filterset_fields = {
        "group": ["exact"],
        "group__telegram_id": ["exact"],
        "user": ["exact"],
        "user__telegram_id": ["exact"],
    }
    search_fields = [
        "group__telegram_id", "group__title", "user__telegram_id",
        "username", "first_name", "last_name",
    ]
    ordering_fields = ["first_spoke_at", "last_spoke_at", "message_count"]


class TronAddressViewSet(viewsets.ModelViewSet):
    queryset = TronAddress.objects.all()
    serializer_class = TronAddressSerializer
    filterset_fields = ["enabled", "status"]
    search_fields = ["address", "label"]
    ordering_fields = ["created_at", "updated_at", "last_checked_at", "balance_sun"]
