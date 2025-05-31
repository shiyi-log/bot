from django.db import models

# Create your models here.
from django.db import models
from django.utils.timezone import now

class Worker(models.Model):
    machine_id = models.CharField(max_length=255, unique=True)
    last_heartbeat = models.DateTimeField(auto_now=True)

    def is_alive(self):
        return (now() - self.last_heartbeat).total_seconds() < 30

    def __str__(self):
        return f"{self.machine_id} ({'🟢' if self.is_alive() else '🔴'})"

class Bot(models.Model):
    name = models.CharField(max_length=255, unique=True)      # 机器人名称（唯一）
    token = models.TextField()                                # Bot Token
    user_id = models.BigIntegerField()                        # 绑定该 Bot 的用户ID
    assigned_worker = models.ForeignKey('Worker', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)      # 创建时间

    class Meta:
        db_table = 'bots_bot'  # 显式指定表名为 bots_bot（保持默认不变）

    def __str__(self):
        return self.name

# ===== Bot 配置表 =====
class BotConfig(models.Model):
    name = models.CharField(max_length=100, unique=True)   # 机器人名称（唯一标识）
    user_id = models.BigIntegerField(null=True, blank=True)  # 新增字段
    token = models.CharField(max_length=255)               # Bot Token
    created_at = models.DateTimeField(auto_now_add=True)   # 创建时间

    class Meta:
        db_table = 'bot_config'                            # 自定义表名

    def __str__(self):
        return f"{self.name} - {self.token[:10]}..."


# ===== Bot 用户表 =====
class BotUser(models.Model):
    bot_name = models.CharField(max_length=100)            # 机器人名称
    user_id = models.BigIntegerField()                     # Telegram 用户ID
    username = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    is_premium = models.BooleanField(default=False)        # 是否为高级用户
    language_code = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)   # 记录时间

    class Meta:
        db_table = 'bot_user'                              # 自定义表名
        unique_together = ('bot_name', 'user_id')          # 保证同一个机器人下用户唯一

    def __str__(self):
        return f"{self.bot_name} - {self.username or self.user_id}"


# ===== 键盘配置表 =====
class BotKeyboardConfig(models.Model):
    bot = models.ForeignKey('BotConfig', on_delete=models.CASCADE)   # 关联机器人
    keyboard_name = models.CharField(max_length=100)                 # 键盘名称
    creator_id = models.BigIntegerField()                            # 创建人 ID
    created_at = models.DateTimeField(auto_now_add=True)             # 创建时间

    class Meta:
        db_table = 'bot_keyboard_config'
        unique_together = ('bot', 'keyboard_name')

    def __str__(self):
        return f"{self.bot.name} - 键盘: {self.keyboard_name}"

# ===== 按钮配置表 =====
class BotKeyboardButton(models.Model):
    keyboard = models.ForeignKey(BotKeyboardConfig, on_delete=models.CASCADE, related_name='buttons')  # 关联键盘
    text = models.CharField(max_length=100)                       # 按钮显示文本
    action_type = models.CharField(max_length=10, choices=[('text', '发送文本'), ('link', '跳转链接')])  # 动作类型
    action_value = models.CharField(max_length=255)               # 发送内容或链接
    row = models.IntegerField(default=1)                          # 按钮所在行
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bot_keyboard_button'

    def __str__(self):
        return f"{self.text} ({self.action_type})"