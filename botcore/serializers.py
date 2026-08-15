from rest_framework import serializers

from .models import BotSettings, TelegramGroup, TelegramGroupMember, TelegramUser, TronAddress
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
    group_telegram_id = serializers.IntegerField(source="group.telegram_id", read_only=True)
    group_title = serializers.CharField(source="group.title", read_only=True)
    telegram_user_id = serializers.IntegerField(source="user.telegram_id", read_only=True)

    class Meta:
        model = TelegramGroupMember
        fields = [
            "id", "group", "group_telegram_id", "group_title", "user", "telegram_user_id",
            "username", "first_name", "last_name", "message_count", "first_spoke_at", "last_spoke_at",
        ]
        read_only_fields = fields


class BotSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotSettings
        fields = [
            "bot_enabled", "welcome_enabled", "welcome_message",
            "tron_monitor_enabled", "tron_poll_interval", "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def validate_tron_poll_interval(self, value):
        if not 5 <= value <= 3600:
            raise serializers.ValidationError("Polling interval must be between 5 and 3600 seconds.")
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
