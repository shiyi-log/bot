import json
import logging
import asyncio
from asgiref.sync import sync_to_async
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.redis_utils import redis_client
from bots.models import BotKeyboardConfig

# ===== 启动时加载键盘到 Redis =====
async def load_keyboards_to_redis(bot_name):
    keyboards = await sync_to_async(list)(
        BotKeyboardConfig.objects.filter(bot__name=bot_name).prefetch_related('buttons')
    )
    count = 0
    for kb in keyboards:
        buttons_data = []
        for btn in kb.buttons.all():
            buttons_data.append({
                "text": btn.text,
                "type": btn.action_type,
                "value": btn.action_value,
                "row": btn.row
            })
        redis_key = f"keyboard:{bot_name}:{kb.keyboard_name}"
        redis_client.set(redis_key, json.dumps(buttons_data))
        count += 1

    redis_client.sadd(f"keyboard:{bot_name}:list", *[kb.keyboard_name for kb in keyboards])
    logging.info(f"🎹 [{bot_name}] 已缓存 {count} 个键盘到 Redis")

# ===== 从 Redis 获取键盘对象 =====
def get_keyboard_from_redis(bot_name, keyboard_name):
    redis_key = f"keyboard:{bot_name}:{keyboard_name}"
    data = redis_client.get(redis_key)
    if not data:
        logging.warning(f"⚠️ 未找到键盘缓存: {redis_key}")
        return None

    buttons = json.loads(data)
    layout = {}
    for btn in buttons:
        if btn["type"] == "text":
            inline_btn = InlineKeyboardButton(text=btn["text"], callback_data=f"kb_text:{btn['value']}")
        elif btn["type"] == "link":
            inline_btn = InlineKeyboardButton(text=btn["text"], url=btn["value"])
        else:
            continue
        layout.setdefault(btn["row"], []).append(inline_btn)

    return InlineKeyboardMarkup(inline_keyboard=[layout[row] for row in sorted(layout)])

# ===== 刷新指定 Bot 的键盘缓存 =====
async def refresh_keyboard_cache(bot_name):
    logging.info(f"🔄 正在刷新 {bot_name} 的键盘缓存...")
    keys = redis_client.smembers(f"keyboard:{bot_name}:list")
    for keyboard_name in keys:
        redis_client.delete(f"keyboard:{bot_name}:{keyboard_name.decode()}")
    redis_client.delete(f"keyboard:{bot_name}:list")
    await load_keyboards_to_redis(bot_name)
    logging.info(f"✅ {bot_name} 键盘缓存刷新完成")

# ===== Redis 监听机制（动态刷新）=====
def listen_keyboard_refresh():
    pubsub = redis_client.pubsub()
    pubsub.subscribe("keyboard_refresh_channel")
    logging.info("📡 启动键盘刷新监听服务...")
    for message in pubsub.listen():
        if message['type'] == 'message':
            bot_name = message['data'].decode()
            logging.info(f"📢 收到刷新通知，Bot: {bot_name}")
            asyncio.run(refresh_keyboard_cache(bot_name))
