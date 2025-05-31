import os
import django

# ✅ 初始化 Django 设置（必须在导入任何 settings 前）
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "multibot.settings")
django.setup()

import asyncio
import logging
import socket
import aiohttp
import threading
import requests
from core.redis_utils import redis_client, REDIS_RUNNING_KEY
from core.bot_service import start_bot
from core.keyboard_utils import listen_keyboard_refresh

# ===== 基础配置 =====
def get_public_ip():
    """获取当前服务器的公网 IP 地址"""
    try:
        response = requests.get("https://api.ipify.org", timeout=3)
        if response.status_code == 200:
            return response.text.strip()
    except Exception:
        pass
    return "unknown"

WORKER_ID = get_public_ip()

API_BASE = "http://127.0.0.1:8000/api/"
CHECK_INTERVAL = 5

# ===== 日志配置 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot_manager.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ===== 启动人工刷新监听线程 =====
threading.Thread(target=listen_keyboard_refresh, daemon=True).start()

# ===== 检查 Redis 中的启动指令 =====
async def watch_and_run():
    logging.info("🔍 正在监听 Redis 启动指令...")
    while True:
        try:
            keys = redis_client.keys("runpy_start:*")
            for key in keys:
                bot_name = key.replace("runpy_start:", "")
                info = redis_client.hgetall(key)

                token = info.get("token")
                if not token:
                    logging.warning(f"⚠️ 启动指令缺少 token: {key}")
                    redis_client.delete(key)
                    continue

                await start_bot(bot_name, token)
                redis_client.delete(key)

        except Exception as e:
            logging.error(f"❌ 检查 Redis 启动指令失败：{e}")

        await asyncio.sleep(CHECK_INTERVAL)

# ===== 主程序入口 =====
async def main():
    logging.info(f"🚀 Bot 启动器 run.py [{WORKER_ID}] 启动")
    await watch_and_run()

if __name__ == '__main__':
    asyncio.run(main())
