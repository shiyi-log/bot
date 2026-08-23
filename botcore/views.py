import re

from django.db import transaction
from django.db.models import Count, Sum
from django.utils.text import slugify
from django.utils import timezone
from rest_framework import generics, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    BotSettings,
    TelegramBot,
    TelegramBotButton,
    TelegramGroup,
    TelegramGroupMember,
    TelegramUser,
    TronAddress,
)
from .serializers import (
    BotSettingsSerializer,
    TelegramBotButtonSerializer,
    TelegramBotSerializer,
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
            "bot_enabled": TelegramBot.objects.filter(enabled=True).exists(),
            "telegram_bots": TelegramBot.objects.count(),
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
    queryset = TelegramGroup.objects.annotate(
        member_count=Count("members__user", distinct=True),
    ).order_by("-last_seen_at")
    serializer_class = TelegramGroupSerializer
    filterset_fields = ["is_active", "group_type"]
    search_fields = ["telegram_id", "title", "username"]
    ordering_fields = ["telegram_id", "first_seen_at", "last_seen_at", "message_count"]


class TelegramGroupMemberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TelegramGroupMember.objects.select_related("bot", "group", "user")
    serializer_class = TelegramGroupMemberSerializer
    filterset_fields = {
        "bot": ["exact"],
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


class TelegramBotViewSet(viewsets.ModelViewSet):
    queryset = TelegramBot.objects.annotate(button_count=Count("buttons")).order_by("name", "id")
    serializer_class = TelegramBotSerializer
    filterset_fields = ["enabled"]
    search_fields = ["name", "username", "telegram_id", "token_env_var"]
    ordering_fields = ["name", "created_at", "updated_at"]

    @action(detail=True, methods=["post"], url_path="clone")
    def clone(self, request, *args, **kwargs):
        source = self.get_object()
        if not source.clone_enabled:
            return Response(
                {"detail": "Cloning is disabled for this bot."},
                status=status.HTTP_403_FORBIDDEN,
            )
        requested_name = str(request.data.get("name", "")).strip()
        requested_env_var = str(request.data.get("token_env_var", "")).strip().upper()
        billing_plan = str(request.data.get("billing_plan", "standard")).strip() or "standard"
        if len(requested_name) > 128:
            raise serializers.ValidationError({"name": "Name must be 128 characters or fewer."})
        if requested_env_var and not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", requested_env_var):
            raise serializers.ValidationError({"token_env_var": "Use an uppercase environment variable name."})
        if requested_env_var and TelegramBot.objects.filter(token_env_var=requested_env_var).exists():
            raise serializers.ValidationError({"token_env_var": "This environment variable name is already in use."})

        with transaction.atomic():
            clone = TelegramBot.objects.create(
                name=requested_name or f"{source.name} 副本",
                username="",
                telegram_id=None,
                token_env_var=requested_env_var or self._next_clone_env_var(source),
                enabled=False,
                welcome_enabled=source.welcome_enabled,
                welcome_message=source.welcome_message,
                clone_enabled=source.clone_enabled,
                cloned_from=source,
            )
            TelegramBotButton.objects.bulk_create([
                TelegramBotButton(
                    bot=clone,
                    text=button.text,
                    url=button.url,
                    row=button.row,
                    position=button.position,
                    enabled=button.enabled,
                )
                for button in source.buttons.all()
            ])

        data = TelegramBotSerializer(clone, context=self.get_serializer_context()).data
        data["billing"] = {
            "status": "reserved",
            "plan": billing_plan,
            "provider": "billing-not-configured",
            "message": "Clone billing integration is reserved and not charged in this template.",
        }
        return Response(data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _next_clone_env_var(source):
        base = slugify(source.name).replace("-", "_").upper() or "BOT"
        base = re.sub(r"[^A-Z0-9_]", "_", base)[:42].strip("_") or "BOT"
        index = 1
        while True:
            candidate = f"{base}_CLONE_{source.pk}_{index}"
            if not TelegramBot.objects.filter(token_env_var=candidate).exists():
                return candidate
            index += 1


class TelegramBotButtonViewSet(viewsets.ModelViewSet):
    queryset = TelegramBotButton.objects.select_related("bot")
    serializer_class = TelegramBotButtonSerializer
    filterset_fields = ["bot", "enabled"]
    search_fields = ["text", "url", "bot__name"]
    ordering_fields = ["row", "position", "created_at", "updated_at"]


class TronAddressViewSet(viewsets.ModelViewSet):
    queryset = TronAddress.objects.all()
    serializer_class = TronAddressSerializer
    filterset_fields = ["enabled", "status"]
    search_fields = ["address", "label"]
    ordering_fields = ["created_at", "updated_at", "last_checked_at", "balance_sun"]
