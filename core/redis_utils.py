import redis
from django.conf import settings

# ===== Redis 配置 =====
redis_client = redis.Redis(
    host=settings.REDIS_CONFIG['host'],
    port=settings.REDIS_CONFIG['port'],
    db=settings.REDIS_CONFIG['db'],
    password=settings.REDIS_CONFIG.get('password'),
    decode_responses=True  # ✅ 添加这个参数
)


# ===== Redis 键名前缀定义 =====
REDIS_KEY = "bot_tokens"                   # 保存所有 Bot 的 token，使用 Hash 存储，结构: {bot_name: token}
REDIS_RUNNING_KEY = "bot_running_status"   # 保存每个 bot 的运行状态
USER_STATE_PREFIX = "user_state:"          # 用户状态状态机的 key 前缀
BLOCK_PREFIX = "blocked_user"              # 屏蔽用户的 key 前缀

# ===== 获取 Redis 中的所有 token 映射 =====
def get_redis_tokens():
    """
    获取 Redis 中保存的所有 Bot Token，返回 dict 结构: {bot_name: token}
    """
    return redis_client.hgetall(REDIS_KEY)
