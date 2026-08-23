import os
import re

from rest_framework import serializers

from .models import (
    BotSettings,
    TelegramBot,
    TelegramBotButton,
    TelegramGroup,
    TelegramGroupMember,
    TelegramLoginAccount,
    TelegramUser,
    TronAddress,
)
from .services.tron import is_valid_tron_address


class TelegramUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = TelegramUser
        fields = [
            "id", "telegram_id", "username", "first_name", "last_name", "display_name",
            "language_code", "is_bot", "is_active", "message_count", "first_seen_at", "last_seen_at",
        ]
        read_only_fields = fields

    def get_display_name(self, obj):
        return " ".join(part for part in [obj.first_name, obj.last_name] if part) or obj.username or str(obj.telegram_id)


class TelegramGroupSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TelegramGroup
        fields = [
            "id", "telegram_id", "title", "username", "group_type", "is_active",
            "message_count", "member_count", "first_seen_at", "last_seen_at",
        ]
        read_only_fields = fields


class TelegramGroupMemberSerializer(serializers.ModelSerializer):
    bot_name = serializers.CharField(source="bot.name", read_only=True, default="")
    group_telegram_id = serializers.IntegerField(source="group.telegram_id", read_only=True)
    group_title = serializers.CharField(source="group.title", read_only=True)
    telegram_user_id = serializers.IntegerField(source="user.telegram_id", read_only=True)

    class Meta:
        model = TelegramGroupMember
        fields = [
            "id", "bot", "bot_name", "group", "group_telegram_id", "group_title", "user", "telegram_user_id",
            "username", "first_name", "last_name", "message_count", "first_spoke_at", "last_spoke_at",
        ]
        read_only_fields = fields


class BotSettingsSerializer(serializers.ModelSerializer):
    telegram_api_hash_configured = serializers.SerializerMethodField()
    telegram_api_hash_preview = serializers.SerializerMethodField()
    telegram_api_hash = serializers.CharField(write_only=True, required=False, allow_blank=True)
    tron_api_key_configured = serializers.SerializerMethodField()
    tron_api_key_preview = serializers.SerializerMethodField()
    tron_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = BotSettings
        fields = [
            "telegram_api_id", "telegram_api_hash", "telegram_api_hash_configured",
            "telegram_api_hash_preview",
            "tron_monitor_enabled", "tron_api_url", "tron_api_key_env_var",
            "tron_api_key", "tron_api_key_configured", "tron_api_key_preview",
            "tron_poll_interval", "updated_at",
        ]
        read_only_fields = [
            "telegram_api_hash_configured", "telegram_api_hash_preview",
            "tron_api_key_configured", "tron_api_key_preview", "updated_at",
        ]

    def get_telegram_api_hash_configured(self, obj):
        return bool(self._telegram_api_hash_value(obj))

    def get_telegram_api_hash_preview(self, obj):
        return self._masked_preview(self._telegram_api_hash_value(obj))

    @staticmethod
    def _telegram_api_hash_value(obj):
        return obj.telegram_api_hash_plain.strip() or os.getenv("TELEGRAM_API_HASH", "").strip()

    def get_tron_api_key_configured(self, obj):
        return bool(obj.tron_api_key.strip() or os.getenv(obj.tron_api_key_env_var, "").strip())

    def get_tron_api_key_preview(self, obj):
        value = obj.tron_api_key.strip() or os.getenv(obj.tron_api_key_env_var, "").strip()
        return self._masked_preview(value)

    @staticmethod
    def _masked_preview(value):
        if not value:
            return ""
        if len(value) <= 6:
            return "*" * len(value)
        return f"{value[:3]}***{value[-3:]}"

    def update(self, instance, validated_data):
        telegram_api_hash = validated_data.pop("telegram_api_hash", serializers.empty)
        if telegram_api_hash is not serializers.empty:
            instance.telegram_api_hash = telegram_api_hash.strip()
        api_key = validated_data.pop("tron_api_key", serializers.empty)
        if api_key is not serializers.empty:
            instance.tron_api_key = api_key.strip()
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not instance.telegram_api_id.strip():
            environment_api_id = os.getenv("TELEGRAM_API_ID", "").strip()
            if environment_api_id.isdecimal() and int(environment_api_id) > 0:
                data["telegram_api_id"] = environment_api_id
        return data

    def validate_telegram_api_id(self, value):
        value = value.strip()
        if value and (not value.isdecimal() or int(value) <= 0):
            raise serializers.ValidationError("Telegram API ID must be a positive integer.")
        return value

    def validate_tron_api_url(self, value):
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise serializers.ValidationError("TRON API URL must use http:// or https://.")
        return value

    def validate_tron_api_key_env_var(self, value):
        value = value.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", value):
            raise serializers.ValidationError(
                "Use an uppercase environment variable name, for example TRONGRID_API_KEY."
            )
        return value

    def validate_tron_poll_interval(self, value):
        if not 5 <= value <= 3600:
            raise serializers.ValidationError("Polling interval must be between 5 and 3600 seconds.")
        return value


class TelegramBotSerializer(serializers.ModelSerializer):
    credential_configured = serializers.SerializerMethodField()
    button_count = serializers.SerializerMethodField()
    clone_count = serializers.SerializerMethodField()
    cloned_from = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TelegramBot
        fields = [
            "id", "name", "username", "telegram_id", "token_env_var", "enabled",
            "welcome_enabled", "welcome_message", "clone_enabled", "credential_configured", "button_count",
            "clone_count", "cloned_from", "created_at", "updated_at",
        ]
        read_only_fields = ["credential_configured", "button_count", "created_at", "updated_at"]

    def get_credential_configured(self, obj):
        return bool(os.getenv(obj.token_env_var, "").strip())

    def get_button_count(self, obj):
        if hasattr(obj, "button_count"):
            return obj.button_count
        return obj.buttons.count()

    def get_clone_count(self, obj):
        return obj.clones.count()

    def validate_token_env_var(self, value):
        value = value.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", value):
            raise serializers.ValidationError("Use an uppercase environment variable name, for example BOT_MAIN_TOKEN.")
        return value


class TelegramLoginAccountSerializer(serializers.ModelSerializer):
    has_session = serializers.SerializerMethodField()
    last_error = serializers.SerializerMethodField()

    class Meta:
        model = TelegramLoginAccount
        fields = [
            "id", "label", "phone", "telegram_id", "username", "first_name",
            "last_name", "status", "has_session", "last_error", "last_checked_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_has_session(self, obj):
        return bool(obj.session_string_plain)

    def get_last_error(self, obj):
        return " ".join(obj.last_error.split())[:500]


class TelegramBotButtonSerializer(serializers.ModelSerializer):
    bot_name = serializers.CharField(source="bot.name", read_only=True)

    class Meta:
        model = TelegramBotButton
        fields = [
            "id", "bot", "bot_name", "text", "url", "row", "position", "enabled",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_row(self, value):
        if not 1 <= value <= 20:
            raise serializers.ValidationError("Row must be between 1 and 20.")
        return value

    def validate_position(self, value):
        if not 1 <= value <= 8:
            raise serializers.ValidationError("Position must be between 1 and 8.")
        return value


class TronAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = TronAddress
        fields = [
            "id", "address", "label", "enabled", "balance_sun", "last_transaction_id",
            "status", "last_error", "last_checked_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "balance_sun", "last_transaction_id", "status", "last_error",
            "last_checked_at", "created_at", "updated_at",
        ]

    def validate_address(self, value):
        value = value.strip()
        if not is_valid_tron_address(value):
            raise serializers.ValidationError("Invalid TRON Base58Check address.")
        return value
