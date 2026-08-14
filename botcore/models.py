from django.db import models


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=128, blank=True)
    last_name = models.CharField(max_length=128, blank=True)
    language_code = models.CharField(max_length=16, blank=True)
    is_bot = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    message_count = models.PositiveIntegerField(default=0)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]

    def __str__(self) -> str:
        return self.username or str(self.telegram_id)


class TelegramGroup(models.Model):
    class GroupType(models.TextChoices):
        GROUP = "group", "Group"
        SUPERGROUP = "supergroup", "Supergroup"
        CHANNEL = "channel", "Channel"

    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    title = models.CharField(max_length=255, blank=True)
    username = models.CharField(max_length=64, blank=True)
    group_type = models.CharField(max_length=16, choices=GroupType.choices)
    is_active = models.BooleanField(default=True)
    message_count = models.PositiveIntegerField(default=0)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]

    def __str__(self) -> str:
        return self.title or str(self.telegram_id)


class BotSettings(models.Model):
    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    bot_enabled = models.BooleanField(default=False)
    welcome_enabled = models.BooleanField(default=True)
    welcome_message = models.TextField(default="欢迎 {first_name} 加入 {group_title}！")
    tron_monitor_enabled = models.BooleanField(default=False)
    tron_poll_interval = models.PositiveIntegerField(default=30)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Bot settings"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(singleton_key=1)
        return obj

    def __str__(self) -> str:
        return "Bot settings"


class TronAddress(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        OK = "ok", "OK"
        ERROR = "error", "Error"

    address = models.CharField(max_length=34, unique=True, db_index=True)
    label = models.CharField(max_length=128, blank=True)
    enabled = models.BooleanField(default=True)
    balance_sun = models.BigIntegerField(default=0)
    last_transaction_id = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    last_error = models.TextField(blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.label or self.address
