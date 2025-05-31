import logging
from django.db import connection
from asgiref.sync import sync_to_async
from bots.models import Bot, BotUser, Worker

def ensure_mysql_connection_alive():
    """确保数据库连接存活，如失效则自动重连"""
    if connection.connection is not None:
        if not connection.is_usable():
            logging.warning("⚠️ MySQL 连接失效，正在尝试重连...")
            connection.close()
    try:
        connection.ensure_connection()
    except Exception as e:
        logging.warning(f"❌ MySQL 自动重连失败：{e}")


# ===== 获取 Bot 的创建人 ID =====
@sync_to_async
def get_bot_creator_id(bot_name):
    ensure_mysql_connection_alive()
    try:
        bot = Bot.objects.only("user_id").get(name=bot_name)
        return bot.user_id
    except Bot.DoesNotExist:
        return None


# ===== 保存 Token 到数据库 =====
@sync_to_async
def save_token_to_db(bot_name: str, token: str, user_id: int):
    ensure_mysql_connection_alive()

    workers = Worker.objects.all()
    alive_workers = [w for w in workers if w.is_alive()]
    if not alive_workers:
        logging.warning("❌ 没有可用的 Worker，无法分配 Bot")
        return False

    # 当前负载映射：Worker.id → 已分配数量
    load_map = {
        w.id: Bot.objects.filter(assigned_worker=w).count()
        for w in alive_workers
    }
    least_loaded_id = min(load_map, key=load_map.get)
    assigned_worker = Worker.objects.get(id=least_loaded_id)

    # 插入或更新
    bot, created = Bot.objects.update_or_create(
        name=bot_name,
        defaults={
            "token": token,
            "user_id": user_id,
            "assigned_worker": assigned_worker
        }
    )

    logging.info(f"{'🆕 新增' if created else '🔄 更新'} Bot：{bot_name} → Worker: {assigned_worker.machine_id}")
    return True


# ===== 保存用户信息 =====
@sync_to_async
def save_user_info(bot_name, user):
    ensure_mysql_connection_alive()
    BotUser.objects.update_or_create(
        bot_name=bot_name,
        user_id=user.id,
        defaults={
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_premium": bool(getattr(user, 'is_premium', False)),
            "language_code": user.language_code
        }
    )


# ===== 获取所有 Token 列表 =====
@sync_to_async
def get_db_tokens():
    ensure_mysql_connection_alive()
    return {bot.name: bot.token for bot in Bot.objects.only("name", "token")}
