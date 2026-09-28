from django.db import models

from botcore.crypto import decrypt_text, encrypt_text


DEFAULT_WELCOME_MESSAGE = "欢迎 {first_name} 加入 {group_title}！"


class TelegramBot(models.Model):
    name = models.CharField(max_length=128)
    username = models.CharField(max_length=64, blank=True)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    token_env_var = models.CharField(max_length=64, unique=True, default="TELEGRAM_BOT_TOKEN")
    enabled = models.BooleanField(default=False)
    welcome_enabled = models.BooleanField(default=True)
    welcome_message = models.TextField(default=DEFAULT_WELCOME_MESSAGE)
    clone_enabled = models.BooleanField(default=True)
    cloned_from = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="clones",
    )
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


class TelegramLoginAccount(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CODE_SENT = "code_sent", "Code sent"
        PASSWORD_REQUIRED = "password_required", "Password required"
        LOGGED_IN = "logged_in", "Logged in"
        SESSION_EXPIRED = "session_expired", "Session expired"
        ERROR = "error", "Error"

    label = models.CharField(max_length=128)
    phone = models.CharField(max_length=32, unique=True)
    telegram_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    username = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=128, blank=True)
    last_name = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    phone_code_hash = models.TextField(blank=True)
    session_string = models.TextField(blank=True)
    login_attempt_id = models.CharField(max_length=32, blank=True)
    login_attempt_started_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(phone=""),
                name="telegram_login_account_phone_not_blank",
            ),
        ]

    @property
    def phone_code_hash_plain(self) -> str:
        return decrypt_text(self.phone_code_hash)

    @property
    def session_string_plain(self) -> str:
        return decrypt_text(self.session_string)

    def save(self, *args, **kwargs):
        self.phone_code_hash = encrypt_text(self.phone_code_hash)
        self.session_string = encrypt_text(self.session_string)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.label


class BotSettings(models.Model):
    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    telegram_api_id = models.CharField(max_length=32, blank=True)
    telegram_api_hash = models.TextField(blank=True)
    tron_monitor_enabled = models.BooleanField(default=False)
    tron_api_url = models.URLField(default="https://api.trongrid.io", max_length=255)
    tron_api_key_env_var = models.CharField(max_length=64, default="TRONGRID_API_KEY")
    # Intentionally plain text per project configuration request. Never expose via API.
    tron_api_key = models.TextField(blank=True, default="")
    tron_poll_interval = models.PositiveIntegerField(default=30)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Bot settings"

    @property
    def telegram_api_hash_plain(self) -> str:
        return decrypt_text(self.telegram_api_hash)

    def save(self, *args, **kwargs):
        self.telegram_api_hash = encrypt_text(self.telegram_api_hash)
        return super().save(*args, **kwargs)

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
    usdt_balance_sun = models.BigIntegerField(default=0)
    resource_snapshot = models.JSONField(default=dict, blank=True)
    permission_snapshot = models.JSONField(default=dict, blank=True)
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


class TronBlockCursor(models.Model):
    network = models.CharField(max_length=32, unique=True, default="mainnet")
    next_block = models.BigIntegerField(default=0)
    last_scanned_block = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.network}: {self.next_block}"


class TronTransferEvent(models.Model):
    block_number = models.BigIntegerField(db_index=True)
    block_timestamp = models.DateTimeField(null=True, blank=True)
    tx_id = models.CharField(max_length=128)
    event_index = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=16)
    contract_address = models.CharField(max_length=34, blank=True)
    from_address = models.CharField(max_length=34)
    to_address = models.CharField(max_length=34)
    amount_sun = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-block_number", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["tx_id", "event_index"], name="unique_tron_transfer_event"),
        ]

    def __str__(self) -> str:
        return f"{self.currency} {self.tx_id}"


class TronAlert(models.Model):
    class Type(models.TextChoices):
        RESOURCE_CHANGED = "resource_changed", "Resource changed"
        AUTHORIZATION_CHANGED = "authorization_changed", "Authorization changed"
        PERMISSION_CHANGED = "permission_changed", "Permission changed"

    address = models.ForeignKey(TronAddress, on_delete=models.CASCADE, related_name="alerts")
    alert_type = models.CharField(max_length=32, choices=Type.choices, db_index=True)
    block_number = models.BigIntegerField(null=True, blank=True, db_index=True)
    block_timestamp = models.DateTimeField(null=True, blank=True)
    tx_id = models.CharField(max_length=128, blank=True, db_index=True)
    event_index = models.PositiveIntegerField(default=0)
    previous_value = models.JSONField(default=dict, blank=True)
    current_value = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["address", "alert_type", "tx_id", "event_index"],
                condition=~models.Q(tx_id=""),
                name="unique_tron_chain_alert",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_alert_type_display()}: {self.address}"
