import asyncio
import socket
import aiohttp
import logging
from datetime import datetime
import redis
import requests

# ===== 配置 =====
API_BASE = "http://127.0.0.1:8000/api/"
def get_public_ip():
    """获取当前机器的公网 IP"""
    try:
        # 推荐使用 ipify 的 API，简洁稳定
        response = requests.get("https://api.ipify.org", timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        print(f"⚠️ 获取公网 IP 失败: {e}")
    return "unknown"
WORKER_ID = get_public_ip()

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# ===== 日志配置 =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def report_heartbeat():
    """定时向 Django 调度中心上报心跳"""
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(API_BASE + "heartbeat/", json={"worker_id": WORKER_ID})
        except Exception as e:
            logger.warning(f"❌ 心跳上报失败: {e}")
        await asyncio.sleep(10)


async def fetch_assigned_bots():
    """从 API 获取当前分配给本机的 Bot 列表"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_BASE + f"assigned-bots/?worker_id={WORKER_ID}") as resp:
                data = await resp.json()
                logger.info(f"📦 获取到 bot 分配列表：{data}")
                return data.get("bots", [])
    except Exception as e:
        logger.error(f"❌ 获取分配失败: {e}")
        return []


async def notify_run_py(bots):
    seen_tokens = set()
    for bot in bots:
        name = bot["name"]
        token = bot["token"]

        if token in seen_tokens:
            logger.warning(f"⚠️ 忽略重复 Token 的 Bot：{name}")
            continue
        seen_tokens.add(token)

        key = f"runpy_start:{name}"
        if redis_client.exists(key):
            continue

        # ✅ 分开写入兼容旧版 redis-py
        redis_client.hset(key, "token", token)
        redis_client.hset(key, "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # ✅ 附加 token → name 映射
        redis_client.hset("token_to_bot", token, name)

        logger.info(f"📨 通知 run.py 启动 Bot：{name}")



async def sync_loop():
    """定时同步任务"""
    while True:
        bots = await fetch_assigned_bots()
        await notify_run_py(bots)
        await asyncio.sleep(15)


async def main():
    logger.info(f"🚀 Worker [{WORKER_ID}] 启动")
    await asyncio.gather(
        report_heartbeat(),
        sync_loop()
    )


if __name__ == "__main__":
    asyncio.run(main())
