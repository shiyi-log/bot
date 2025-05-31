import os
import django
import logging
from django.core.management import call_command
from datetime import datetime, timedelta
import redis

# ===== 初始化 Django 环境（必须放在最前）=====
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "multibot.settings")
django.setup()

# ===== 日志配置 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("django_server.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ===== 启动 APScheduler =====
from multibot.scheduler import start_scheduler

logging.info("🟢 Django 环境初始化完成")
logging.info("⏰ 启动 APScheduler 定时器 ...")
start_scheduler()

# ===== 检查存活 Worker（从 Redis 获取状态）=====
from core.redis_utils import redis_client

def print_active_workers():
    prefix = "worker_status:"
    keys = redis_client.keys(f"{prefix}*")
    active = []

    for key in keys:
        last_seen = redis_client.get(key)
        if last_seen:
            try:
                last_seen_dt = datetime.strptime(last_seen.decode(), "%Y-%m-%d %H:%M:%S")
                if datetime.now() - last_seen_dt < timedelta(seconds=120):
                    worker_name = key.decode().replace(prefix, "")
                    active.append(worker_name)
            except Exception as e:
                logging.warning(f"❌ 解析 worker 状态失败: {e}")

    if active:
        logging.info(f"✅ 当前存活 Worker 共 {len(active)} 个: {active}")
    else:
        logging.warning("⚠️ 当前没有存活的 Worker")

print_active_workers()

# ===== 启动 Django 开发服务器 =====
logging.info("🌐 启动 Django 开发服务器 http://0.0.0.0:8000")
call_command("runserver", "0.0.0.0:8000")
