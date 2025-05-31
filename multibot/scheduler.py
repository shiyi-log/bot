import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils.timezone import now
from bots.models import Bot, Worker

logger = logging.getLogger(__name__)

def reassign_bots():
    logger.info("🔁 正在执行自动重分配任务...")
    bots = Bot.objects.all()
    workers = [w for w in Worker.objects.all() if w.is_alive()]

    if not workers:
        logger.warning("❌ 无可用 Worker，跳过重分配")
        return

    load = {w.id: Bot.objects.filter(assigned_worker=w).count() for w in workers}

    for bot in bots:
        if not bot.assigned_worker or not bot.assigned_worker.is_alive():
            least_loaded_id = min(load, key=load.get)
            new_worker = Worker.objects.get(id=least_loaded_id)
            bot.assigned_worker = new_worker
            bot.save()
            load[least_loaded_id] += 1
            logger.info(f"✅ Bot [{bot.name}] 重新分配给 Worker [{new_worker.machine_id}]")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(reassign_bots, 'interval', seconds=60)  # 每 60 秒执行一次
    scheduler.start()
    logger.info("✅ 启动 APScheduler 定时器（每分钟执行 Bot 重分配）")
