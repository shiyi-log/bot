from django.db import models


DEFAULT_WELCOME_MESSAGE = "欢迎 {first_name} 加入 {group_title}！"


class TelegramBot(models.Model):
    name = models.CharField(max_length=128)
    username = models.CharField(max_length=64, blank=True)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    token_env_var = models.CharField(max_length=64, unique=True, default="TELEGRAM_BOT_TOKEN")
    enabled = models.BooleanField(default=False)
    welcome_enabled = models.BooleanField(default=True)
    welcome_message = models.TextField(default=DEFAULT_WELCOME_MESSAGE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    @classmethod
    def load_default(cls):
        bot, _ = cls.objects.get_or_create(
            token_env_var="TELEGRAM_BOT_TOKEN",
            defaults={"name": "默认机器人"},
        )
        return bot

    def __str__(self) -> str:
        return self.name


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


class TelegramBotUser(models.Model):
    bot = models.ForeignKey(TelegramBot, on_delete=models.CASCADE, related_name="users")
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="bots")
    message_count = models.PositiveIntegerField(default=0)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]
        constraints = [
            models.UniqueConstraint(fields=["bot", "user"], name="unique_telegram_bot_user"),
        ]


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


class TelegramGroupMember(models.Model):
    bot = models.ForeignKey(
        TelegramBot,
        on_delete=models.CASCADE,
        related_name="group_members",
    )
    group = models.ForeignKey(TelegramGroup, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="group_memberships")
    username = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=128, blank=True)
    last_name = models.CharField(max_length=128, blank=True)
    message_count = models.PositiveIntegerField(default=0)
    first_spoke_at = models.DateTimeField(auto_now_add=True)
    last_spoke_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_spoke_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["bot", "group", "user"],
                name="unique_telegram_bot_group_member",
            ),
        ]
        indexes = [
            models.Index(fields=["group", "last_spoke_at"], name="tg_member_group_last_idx"),
            models.Index(fields=["user", "last_spoke_at"], name="tg_member_user_last_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.group} / {self.user}"


class BotSettings(models.Model):
    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    tron_monitor_enabled = models.BooleanField(default=False)
    tron_api_url = models.URLField(default="https://api.trongrid.io", max_length=255)
    tron_api_key_env_var = models.CharField(max_length=64, default="TRONGRID_API_KEY")
    # Intentionally plain text per project configuration request. Never expose via API.
    tron_api_key = models.TextField(blank=True, default="")
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


class TelegramBotButton(models.Model):
    bot = models.ForeignKey(TelegramBot, on_delete=models.CASCADE, related_name="buttons")
    text = models.CharField(max_length=64)
    url = models.URLField(max_length=500)
    row = models.PositiveSmallIntegerField(default=1)
    position = models.PositiveSmallIntegerField(default=1)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["row", "position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["bot", "row", "position"],
                name="unique_telegram_bot_button_position",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.bot}: {self.text}"


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
