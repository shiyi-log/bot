import os
import re
import uuid
from datetime import timedelta

from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Count, Sum
from django.utils.text import slugify
from django.utils import timezone
from rest_framework import generics, mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    BotSettings,
    TelegramBot,
    TelegramBotButton,
    TelegramGroup,
    TelegramGroupMember,
    TelegramLoginAccount,
    TelegramUser,
    TronAddress,
    TronTransferEvent,
)
from .serializers import (
    BotSettingsSerializer,
    TelegramBotButtonSerializer,
    TelegramBotSerializer,
    TelegramGroupSerializer,
    TelegramGroupMemberSerializer,
    TelegramLoginAccountSerializer,
    TelegramUserSerializer,
    TronAddressSerializer,
    TronTransferEventSerializer,
)
from .services import telegram_accounts as telegram_account_service
from .services.telegram_accounts import TelegramAccountError, normalize_phone
from .services.tron import TronGridProvider, apply_snapshot


LOGIN_ATTEMPT_TTL = timedelta(minutes=2)


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


class TelegramLoginAccountViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = TelegramLoginAccount.objects.all()
    serializer_class = TelegramLoginAccountSerializer
    search_fields = [
        "phone",
        "telegram_id",
        "username",
        "first_name",
        "last_name",
        "label",
    ]

    @action(detail=False, methods=["post"], url_path="login/start")
    def login_start(self, request):
        phone_value = request.data.get("phone", "")
        try:
            phone = normalize_phone(phone_value)
        except TelegramAccountError as exc:
            return self._error_response(exc)
        label = str(request.data.get("label", "")).strip()
        if len(label) > 128:
            raise serializers.ValidationError({"label": "Ensure this field has no more than 128 characters."})
        try:
            telegram_account_service.validate_runtime_configuration()
        except TelegramAccountError as exc:
            return self._error_response(exc)
        try:
            account, attempt_id = self._begin_login_attempt(phone, label)
        except OperationalError as exc:
            if self._is_database_lock_error(exc):
                return self._database_busy_response()
            raise
        if attempt_id is None:
            return self._conflict_response()

        try:
            result = telegram_account_service.send_login_code(phone)
        except TelegramAccountError as exc:
            try:
                recorded = self._fail_login_attempt(account.pk, attempt_id, exc.message)
            except OperationalError as database_error:
                if self._is_database_lock_error(database_error):
                    return self._database_busy_response()
                raise
            if not recorded:
                return self._conflict_response()
            return self._error_response(exc)

        try:
            account = self._complete_login_attempt(account.pk, attempt_id, result)
        except OperationalError as exc:
            if self._is_database_lock_error(exc):
                return self._database_busy_response()
            raise
        if account is None:
            return self._conflict_response()

        return Response(self._step_response(account, "code"))

    @classmethod
    def _begin_login_attempt(cls, phone, label):
        with transaction.atomic():
            account = TelegramLoginAccount.objects.select_for_update().filter(
                phone=phone,
            ).first()
            if account is None:
                try:
                    with transaction.atomic():
                        account = TelegramLoginAccount.objects.create(
                            phone=phone,
                            label=label or phone,
                        )
                except IntegrityError:
                    account = TelegramLoginAccount.objects.select_for_update().get(
                        phone=phone,
                    )

            now = timezone.now()
            attempt_is_fresh = (
                account.status == TelegramLoginAccount.Status.PENDING
                and bool(account.login_attempt_id)
                and account.login_attempt_started_at is not None
                and account.login_attempt_started_at >= now - LOGIN_ATTEMPT_TTL
            )
            if attempt_is_fresh:
                return account, None

            attempt_id = uuid.uuid4().hex
            if label:
                account.label = label
            account.status = TelegramLoginAccount.Status.PENDING
            account.login_attempt_id = attempt_id
            account.login_attempt_started_at = now
            account.last_error = ""
            account.save(update_fields=[
                "label",
                "status",
                "login_attempt_id",
                "login_attempt_started_at",
                "last_error",
                "updated_at",
            ])
            return account, attempt_id

    @classmethod
    def _complete_login_attempt(cls, account_id, attempt_id, result):
        with transaction.atomic():
            account = cls._lock_account(account_id)
            if account is None:
                return None
            if account.login_attempt_id != attempt_id:
                return None
            account.phone = result.phone
            account.phone_code_hash = result.phone_code_hash
            account.session_string = result.session_string
            account.status = TelegramLoginAccount.Status.CODE_SENT
            account.login_attempt_id = ""
            account.login_attempt_started_at = None
            account.last_error = ""
            account.save()
            return account

    @classmethod
    def _fail_login_attempt(cls, account_id, attempt_id, message):
        with transaction.atomic():
            account = cls._lock_account(account_id)
            if account is None:
                return False
            if account.login_attempt_id != attempt_id:
                return False
            account.status = TelegramLoginAccount.Status.ERROR
            account.login_attempt_id = ""
            account.login_attempt_started_at = None
            account.last_error = cls._safe_error(message)
            account.save(update_fields=[
                "status",
                "login_attempt_id",
                "login_attempt_started_at",
                "last_error",
                "updated_at",
            ])
            return True

    @staticmethod
    def _is_database_lock_error(exc):
        message = str(exc).lower()
        return "locked" in message or "busy" in message

    @staticmethod
    def _lock_account(account_id):
        return TelegramLoginAccount.objects.select_for_update().filter(
            pk=account_id,
        ).first()

    @action(detail=False, methods=["post"], url_path="login/code")
    def login_code(self, request):
        account = self._input_account(request.data.get("account_id"))
        code = str(request.data.get("code", "")).strip()
        if not code:
            raise serializers.ValidationError({"detail": "验证码不能为空。"})
        if account.status != TelegramLoginAccount.Status.CODE_SENT:
            return self._state_error(TelegramLoginAccount.Status.CODE_SENT)
        phone_code_hash = account.phone_code_hash_plain
        session_string = account.session_string_plain
        attempt_snapshot = self._attempt_snapshot(account)
        if not phone_code_hash or not session_string:
            raise serializers.ValidationError({"detail": "登录状态不完整，请重新发送验证码。"})

        try:
            result = telegram_account_service.sign_in_with_code(
                account.phone,
                code,
                phone_code_hash,
                session_string,
            )
        except TelegramAccountError as exc:
            if not self._record_error(account.pk, attempt_snapshot, exc.message):
                return self._conflict_response()
            return self._error_response(exc)

        with transaction.atomic():
            locked = self._lock_account(account.pk)
            if locked is None:
                return self._conflict_response()
            if not self._matches_attempt(locked, attempt_snapshot):
                return self._conflict_response()
            locked.session_string = result.session_string
            locked.phone_code_hash = ""
            locked.last_error = ""
            if result.requires_password:
                locked.status = TelegramLoginAccount.Status.PASSWORD_REQUIRED
                locked.save()
                return Response(self._step_response(locked, "password"))
            if result.user is None:
                return self._invalid_service_result(locked, TelegramLoginAccount.Status.CODE_SENT)
            self._complete_login(locked, result.user)
            locked.save()
        return Response(self._step_response(locked, "complete"))

    @action(detail=False, methods=["post"], url_path="login/password")
    def login_password(self, request):
        account = self._input_account(request.data.get("account_id"))
        password = str(request.data.get("password", ""))
        if not password:
            raise serializers.ValidationError({"detail": "二级密码不能为空。"})
        if account.status != TelegramLoginAccount.Status.PASSWORD_REQUIRED:
            return self._state_error(TelegramLoginAccount.Status.PASSWORD_REQUIRED)
        session_string = account.session_string_plain
        attempt_snapshot = self._attempt_snapshot(account)
        if not session_string:
            raise serializers.ValidationError({"detail": "登录会话不存在，请重新登录。"})

        try:
            result = telegram_account_service.sign_in_with_password(password, session_string)
        except TelegramAccountError as exc:
            if not self._record_error(account.pk, attempt_snapshot, exc.message):
                return self._conflict_response()
            return self._error_response(exc)

        with transaction.atomic():
            locked = self._lock_account(account.pk)
            if locked is None:
                return self._conflict_response()
            if not self._matches_attempt(locked, attempt_snapshot):
                return self._conflict_response()
            if result.user is None or result.requires_password:
                return self._invalid_service_result(
                    locked,
                    TelegramLoginAccount.Status.PASSWORD_REQUIRED,
                )
            locked.session_string = result.session_string
            locked.phone_code_hash = ""
            locked.last_error = ""
            self._complete_login(locked, result.user)
            locked.save()
        return Response(self._step_response(locked, "complete"))

    @action(detail=True, methods=["post"], url_path="check")
    def check(self, request, *args, **kwargs):
        account = self.get_object()
        session_string = account.session_string_plain
        attempt_snapshot = self._attempt_snapshot(account)
        if not session_string:
            raise serializers.ValidationError({"detail": "登录会话不存在，请重新登录。"})
        try:
            result = telegram_account_service.check_session(session_string)
        except TelegramAccountError as exc:
            if exc.code == "session_unauthorized":
                updated_account = self._mark_session_expired(
                    account.pk,
                    attempt_snapshot,
                    exc.message,
                )
                if updated_account is None:
                    return self._conflict_response()
                return Response(self.get_serializer(updated_account).data)
            else:
                if not self._record_error(account.pk, attempt_snapshot, exc.message):
                    return self._conflict_response()
            return self._error_response(exc)

        with transaction.atomic():
            locked = self._lock_account(account.pk)
            if locked is None:
                return self._conflict_response()
            if not self._matches_attempt(locked, attempt_snapshot):
                return self._conflict_response()
            locked.last_checked_at = timezone.now()
            locked.last_error = ""
            if result.authorized and result.user is not None:
                self._complete_login(locked, result.user)
            else:
                locked.status = TelegramLoginAccount.Status.SESSION_EXPIRED
            locked.save()
        return Response(self.get_serializer(locked).data)

    def _input_account(self, account_id):
        if isinstance(account_id, bool):
            account_id = None
        try:
            account_id = int(account_id)
        except (TypeError, ValueError):
            raise serializers.ValidationError({"account_id": "A valid account ID is required."})
        account = TelegramLoginAccount.objects.filter(pk=account_id).first()
        if account is None:
            raise serializers.ValidationError({"account_id": "Account does not exist."})
        return account

    def _step_response(self, account, next_step):
        return {
            "account": self.get_serializer(account).data,
            "account_id": account.pk,
            "next_step": next_step,
        }

    @staticmethod
    def _next_step(account):
        if account.status == TelegramLoginAccount.Status.PASSWORD_REQUIRED:
            return "password"
        if account.status == TelegramLoginAccount.Status.LOGGED_IN:
            return "complete"
        return "code"

    @staticmethod
    def _complete_login(account, user):
        account.telegram_id = user.telegram_id
        account.username = user.username
        account.first_name = user.first_name
        account.last_name = user.last_name
        account.status = TelegramLoginAccount.Status.LOGGED_IN
        account.last_checked_at = timezone.now()

    @staticmethod
    def _safe_error(message):
        return " ".join(str(message).split())[:500]

    @staticmethod
    def _attempt_snapshot(account):
        return {
            "status": account.status,
            "phone_code_hash": account.phone_code_hash_plain,
            "session_string": account.session_string_plain,
            "updated_at": account.updated_at,
        }

    @staticmethod
    def _matches_attempt(account, snapshot):
        return (
            account.status == snapshot["status"]
            and account.phone_code_hash_plain == snapshot["phone_code_hash"]
            and account.session_string_plain == snapshot["session_string"]
            and account.updated_at == snapshot["updated_at"]
        )

    @classmethod
    def _record_error(cls, account_id, attempt_snapshot, message):
        with transaction.atomic():
            account = cls._lock_account(account_id)
            if account is None or not cls._matches_attempt(account, attempt_snapshot):
                return False
            account.last_error = cls._safe_error(message)
            account.save(update_fields=["last_error"])
            return True

    @classmethod
    def _mark_session_expired(cls, account_id, attempt_snapshot, message):
        with transaction.atomic():
            account = cls._lock_account(account_id)
            if account is None or not cls._matches_attempt(account, attempt_snapshot):
                return None
            account.status = TelegramLoginAccount.Status.SESSION_EXPIRED
            account.last_error = cls._safe_error(message)
            account.last_checked_at = timezone.now()
            account.save(update_fields=["status", "last_error", "last_checked_at", "updated_at"])
            return account

    def _invalid_service_result(self, account, expected_status):
        message = "Telegram 返回了无效的登录结果，请重试。"
        if account.status == expected_status:
            account.last_error = message
            account.save(update_fields=["last_error"])
        return Response({"detail": message}, status=status.HTTP_502_BAD_GATEWAY)

    @staticmethod
    def _state_error(expected_status):
        return Response(
            {"detail": f"账号状态不匹配，需要 {expected_status} 状态。"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def _conflict_response():
        return Response(
            {"detail": "账号状态已更新，请刷新后重试。"},
            status=status.HTTP_409_CONFLICT,
        )

    @staticmethod
    def _database_busy_response():
        return Response(
            {"detail": "账号状态正被其他请求更新，请稍后重试。"},
            status=status.HTTP_409_CONFLICT,
        )

    @staticmethod
    def _error_response(exc):
        status_code = status.HTTP_400_BAD_REQUEST
        if exc.code in {"network_disabled", "credentials_missing", "invalid_api_id"}:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif exc.code == "flood_wait":
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif exc.code in {"timeout", "network_error", "telegram_error"}:
            status_code = status.HTTP_502_BAD_GATEWAY
        response = {"detail": TelegramLoginAccountViewSet._safe_error(exc.message)}
        if exc.retry_after is not None:
            response["retry_after"] = exc.retry_after
        return Response(response, status=status_code)


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

    @action(detail=True, methods=["post"])
    def check(self, request, pk=None):
        if os.getenv("ENABLE_TRON_NETWORK", "0") != "1":
            return Response({"detail": "TRON network is disabled; set ENABLE_TRON_NETWORK=1 explicitly."}, status=503)
        settings = BotSettings.load()
        api_key = settings.tron_api_key.strip() or os.getenv(settings.tron_api_key_env_var, "").strip()
        if not api_key:
            return Response({"detail": f"{settings.tron_api_key_env_var} is required."}, status=503)
        address = self.get_object()
        try:
            snapshot = TronGridProvider(settings.tron_api_url, api_key, os.getenv("TRON_USDT_CONTRACT", "")).get_snapshot(address.address)
            apply_snapshot(address, snapshot)
        except Exception as exc:
            address.status = TronAddress.Status.ERROR
            address.last_error = str(exc)[:1000]
            address.last_checked_at = timezone.now()
            address.save(update_fields=["status", "last_error", "last_checked_at", "updated_at"])
            return Response({"detail": "TRON address check failed."}, status=502)
        return Response(self.get_serializer(address).data)


class TronTransferEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TronTransferEvent.objects.all()
    serializer_class = TronTransferEventSerializer
    filterset_fields = ["currency", "block_number", "from_address", "to_address"]
    search_fields = ["tx_id", "from_address", "to_address", "contract_address"]
    ordering_fields = ["block_number", "block_timestamp", "created_at"]
