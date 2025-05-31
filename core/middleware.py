import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bots.models import Bot
from core.redis_utils import redis_client, BLOCK_PREFIX

# === Redis Key 构造封装 ===
def get_block_key(bot_name, user_id):
    return f"{BLOCK_PREFIX}:{bot_name}:{user_id}"

def get_creator_cache_key(bot_name):
    return f"creator:{bot_name}"

def get_forward_map_key(bot_id):
    return f"forward_map:{bot_id}"

# === 获取或从数据库加载创建人 ID ===
async def get_or_fetch_creator_id(bot_name, ttl=36000):
    key = get_creator_cache_key(bot_name)
    creator_id = redis_client.get(key)

    if creator_id:
        logging.debug(f"✅ 从 Redis 缓存获取到创建人 ID：{creator_id}")
        return int(creator_id)

    logging.info(f"🔍 Redis 未命中创建人 ID：{key}，准备从数据库查找")
    try:
        bot_row = await Bot.objects.aget(name=bot_name)
        creator_id = bot_row.user_id
        redis_client.setex(key, ttl, creator_id)
        logging.info(f"✅ 数据库查找到创建人 ID：{creator_id}，已缓存 {ttl} 秒")
        return creator_id
    except Bot.DoesNotExist:
        logging.warning(f"❌ Bot [{bot_name}] 在数据库中不存在，无法获取创建人 ID")
        return None
    except Exception as e:
        logging.error(f"❌ 查询数据库异常: {e}")
        return None

# === 主中间件类 ===
class LoggingAndForwardMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            user = event.from_user
            bot_name = data.get('bot_name')
            bot_instance = data.get('bot')
            chat_type = event.chat.type

            nickname = f"{user.first_name or ''}{user.last_name or ''}"
            username = f"@{user.username}" if user.username else "(无用户名)"
            content_type = event.content_type
            content = event.text or f"[{content_type}]"

            log_prefix = {
                "private": "📨 私聊",
                "group": f"👥 群组 [{event.chat.title}]",
                "supergroup": f"👥 超级群组 [{event.chat.title}]",
                "channel": f"📢 频道 [{event.chat.title}]"
            }.get(chat_type, f"📦 其他 [{chat_type}]")

            log_msg = (
                f"{log_prefix} | [Bot:{bot_name}] | 用户ID:{user.id} | 昵称:{nickname} | "
                f"用户名:{username} | 类型:{content_type} | 内容:{content}"
            )
            logging.info(log_msg)

            # === 获取创建人 ID ===
            creator_id = await get_or_fetch_creator_id(bot_name)
            if not creator_id:
                return await handler(event, data)

            # === 创建人回复逻辑 ===
            if event.reply_to_message and user.id == creator_id:
                reply_text = event.reply_to_message.text
                if reply_text and "用户ID:" in reply_text:
                    try:
                        target_user_id = int(reply_text.split("用户ID:")[1].split("\n")[0].strip())
                        await bot_instance.send_message(chat_id=target_user_id, text=event.text)
                        logging.info(f"📨 已将创建人回复发送给用户 {target_user_id}")
                    except Exception as e:
                        logging.error(f"❌ 回复转发失败（用户ID提示模式）：{e}")
                    return await handler(event, data)

                if event.reply_to_message.forward_from:
                    target_user_id = event.reply_to_message.forward_from.id
                else:
                    bot_info = await bot_instance.get_me()
                    redis_hash_key = get_forward_map_key(bot_info.id)
                    cached_id = redis_client.hget(redis_hash_key, event.reply_to_message.message_id)
                    target_user_id = int(cached_id) if cached_id else None

                if target_user_id:
                    try:
                        await bot_instance.send_message(chat_id=target_user_id, text=event.text)
                        logging.info(f"📨 已将创建人回复发送给用户 {target_user_id}")
                    except Exception as e:
                        logging.error(f"❌ 回复转发失败（forward/cached 模式）：{e}")
                else:
                    logging.info("⚠️ 无法识别回复目标（无 forward_from 且未命中缓存）")

                return await handler(event, data)

            # === 私聊转发逻辑 ===
            if chat_type == "private" and creator_id and user.id != creator_id:
                block_key = get_block_key(bot_name, user.id)
                if redis_client.exists(block_key):
                    logging.info(f"⏸️ 用户 [{user.id}] 在 Bot [{bot_name}] 被屏蔽，跳过转发")
                else:
                    try:
                        info_text = (
                            f"📨 消息提醒\n"
                            f"👤 用户ID: {user.id}\n"
                            f"📝 昵称: {nickname}\n"
                            f"🔗 用户名: {username}\n"
                            f"💬 温馨提示：可以直接右键回复或者长按回复用户"
                        )
                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[[InlineKeyboardButton(
                                text="🔕 屏蔽此用户 10 分钟",
                                callback_data=f"block:{bot_name}:{user.id}"
                            )]]
                        )

                        await bot_instance.send_message(creator_id, info_text, reply_markup=keyboard)
                        forwarded_msg = await bot_instance.forward_message(
                            chat_id=creator_id,
                            from_chat_id=event.chat.id,
                            message_id=event.message_id
                        )

                        bot_info = await bot_instance.get_me()
                        redis_hash_key = get_forward_map_key(bot_info.id)
                        redis_client.hset(redis_hash_key, forwarded_msg.message_id, user.id)
                        if redis_client.ttl(redis_hash_key) == -1:
                            redis_client.expire(redis_hash_key, 3600)

                    except Exception as e:
                        logging.error(f"❌ 转发失败：{e}")

        return await handler(event, data)
