from datetime import timedelta

import redis
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.timezone import now
from .models import Worker, Bot
import json
import logging

logger = logging.getLogger(__name__)
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def all_bot_status(request):
    workers = redis_client.keys("worker_bots:*")
    result = {}
    for wk in workers:
        worker_id = wk.split(":")[1]
        bot_names = redis_client.smembers(wk)
        bot_info = {}
        for name in bot_names:
            status = redis_client.hgetall(f"bot_status:{name}")
            bot_info[name] = status
        result[worker_id] = bot_info
    return JsonResponse(result)
def assigned_bots(request):
    mid = request.GET.get("worker_id")
    worker = Worker.objects.filter(machine_id=mid).first()
    if not worker:
        logger.warning(f"❌ 未找到 worker：{mid}")
        return JsonResponse({"bots": []})

    bots = Bot.objects.filter(assigned_worker=worker)
    result = [{"name": b.name, "token": b.token} for b in bots]

    # ✅ 打印日志
    logger.info(f"📦 分配给 worker [{mid}] 的 bots: {result}")

    return JsonResponse({"bots": result})

@csrf_exempt
def heartbeat(request):
    """Worker 上报心跳"""
    try:
        data = json.loads(request.body)
        worker_id = data.get("worker_id")
        if not worker_id:
            return JsonResponse({"error": "worker_id missing"}, status=400)

        # ✅ 保存或更新 worker 信息（会创建或刷新数据库记录）
        Worker.objects.update_or_create(
            machine_id=worker_id,  # 对应 WORKER_ID（例如公网 IP）
            defaults={"last_heartbeat": now()}  # 更新时间戳
        )

        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



# def assigned_bots(request):
#     """Worker 拉取分配给自己的 Bot"""
#     worker_id = request.GET.get("worker_id")
#     if not worker_id:
#         return JsonResponse({"bots": []})
#     worker = Worker.objects.filter(machine_id=worker_id).first()
#     if not worker:
#         return JsonResponse({"bots": []})
#     bots = Bot.objects.filter(assigned_worker=worker)
#     return JsonResponse({"bots": [{"name": b.name, "token": b.token} for b in bots]})


@csrf_exempt
def register_bot(request):
    """注册新的 Bot（仅开发用）"""
    try:
        data = json.loads(request.body)
        name = data.get("name")
        token = data.get("token")
        if not name or not token:
            return JsonResponse({"error": "name/token required"}, status=400)
        Bot.objects.update_or_create(name=name, defaults={"token": token})
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def reassign_all_bots(request):
    """重新分配所有 bot 到存活 worker"""
    bots = Bot.objects.all()
    workers = [w for w in Worker.objects.all() if w.is_alive()]
    if not workers:
        return JsonResponse({"error": "no available workers"}, status=500)
    load = {w.id: Bot.objects.filter(assigned_worker=w).count() for w in workers}
    for bot in bots:
        if not bot.assigned_worker or not bot.assigned_worker.is_alive():
            least_loaded = min(load, key=load.get)
            bot.assigned_worker = Worker.objects.get(id=least_loaded)
            bot.save()
            load[least_loaded] += 1
    return JsonResponse({"status": "reassigned"})


def all_tokens(request):
    """提供全部 Bot Token 列表（给管理器同步使用）"""
    bots = Bot.objects.all()
    return JsonResponse({
        "bots": [{"name": b.name, "token": b.token} for b in bots]
    })

def system_status(request):
    """提供系统实时状态：Worker 总数、活跃数、Bot 总数、未分配 Bot 列表"""
    # 定义活跃判断时间范围（30 秒内心跳）
    threshold = now() - timedelta(seconds=30)

    workers = Worker.objects.all()
    bots = Bot.objects.all()

    active_workers = [w.machine_id for w in workers if w.last_heartbeat and w.last_heartbeat > threshold]
    unassigned_bots = bots.filter(assigned_worker__isnull=True)

    return JsonResponse({
        "worker_total": workers.count(),
        "worker_active_count": len(active_workers),
        "worker_active_list": active_workers,
        "bot_total": bots.count(),
        "bot_unassigned_count": unassigned_bots.count(),
        "bot_unassigned_list": list(unassigned_bots.values_list("name", flat=True)),
    })

