import asyncio
import logging
import aiohttp

from core.redis_utils import redis_client, REDIS_KEY
from core.bot_service import start_bot, stop_bot

CHECK_INTERVAL = 30
API_BASE = "http://127.0.0.1:8000/api/"


async def fetch_tokens_from_api() -> dict[str, str]:
    """从调度系统 API 拉取所有 Bot Token"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_BASE + "all-tokens/") as resp:
                data = await resp.json()
                return {item["name"]: item["token"] for item in data.get("bots", [])}
    except Exception as e:
        logging.error(f"❌ 无法从 API 获取 Token：{e}")
        return {}


def get_redis_tokens() -> dict[str, str]:
    """从 Redis 获取当前缓存中的 Bot Token"""
    return redis_client.hgetall(REDIS_KEY)


async def sync_db_and_redis():
    """同步 API 返回的 Token 和 Redis 缓存状态"""
    db_tokens = await fetch_tokens_from_api()
    redis_tokens = get_redis_tokens()

    added = updated = deleted = 0

    # 更新新增/修改的 token
    for name, token in db_tokens.items():
        if name not in redis_tokens:
            redis_client.hset(REDIS_KEY, name, token)
            logging.info(f"🆕 新增 Token：{name}")
            added += 1
        elif redis_tokens[name] != token:
            redis_client.hset(REDIS_KEY, name, token)
            logging.info(f"🔄 更新 Token：{name}")
            updated += 1

    # 删除已不存在的 bot
    for name in list(redis_tokens.keys()):
        if name not in db_tokens:
            redis_client.hdel(REDIS_KEY, name)
            await stop_bot(name)
            logging.info(f"❌ 删除 Token 并停止 Bot：{name}")
            deleted += 1

    if added or updated or deleted:
        logging.info(f"✅ 同步完成：新增 {added}，更新 {updated}，删除 {deleted}")
    else:
        logging.info("🔹 无需同步，状态一致")


async def start_bots_if_needed():
    """启动尚未运行的 Bot"""
    redis_tokens = get_redis_tokens()
    for name, token in redis_tokens.items():
        running_status = redis_client.hget("bot_running_status", name)
        if not running_status:
            logging.info(f"🚀 启动新发现的 Bot：{name}")
            asyncio.create_task(start_bot(name, token))


async def monitor_loop():
    """定时执行同步与启动检查任务"""
    logging.info(f"🔁 定时任务启动，每 {CHECK_INTERVAL} 秒执行一次同步与检查...")
    while True:
        await sync_db_and_redis()
        await start_bots_if_needed()
        await asyncio.sleep(CHECK_INTERVAL)


async def main():
    """主启动函数"""
    logging.info("🚀 初始化阶段：同步 Token 并启动 Bot ...")
    await sync_db_and_redis()
    await start_bots_if_needed()

    # 启动监控任务
    asyncio.create_task(monitor_loop())
    logging.info("🤖 Bot 管理器已启动，开始监听与管理所有 Bot ...")

    # 保持主循环常驻
    while True:
        await asyncio.sleep(3600)
