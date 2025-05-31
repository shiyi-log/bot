import logging
from aiogram import Dispatcher, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from asgiref.sync import sync_to_async

from bots.models import BotKeyboardButton
from core.redis_utils import redis_client, USER_STATE_PREFIX, REDIS_KEY
from core.utils import save_user_info, save_token_to_db, get_bot_creator_id
from core.redis_utils import get_redis_tokens


def register_bot_commands(dp: Dispatcher, bot_name: str, bot: Bot, start_bot_func):
    logging.info(f"🔧 注册指令处理器成功：Bot [{bot_name}]")

    @dp.message(Command("start"))
    async def start_cmd(message: Message):
        user = message.from_user
        redis_client.delete(USER_STATE_PREFIX + str(user.id))
        await save_user_info(bot_name, user)
        logging.info(f"🚀 用户触发 /start | Bot:[{bot_name}] | 用户ID:{user.id}")
        await message.reply("👋 欢迎使用双向机器人，使用 /kelong 命令克隆此机器人~")

    @dp.message(Command("kelong"))
    async def kelong_cmd(message: Message):
        redis_client.set(USER_STATE_PREFIX + str(message.from_user.id), "waiting_token")
        logging.info(f"🟡 用户 [{message.from_user.id}] 进入等待 Token 状态")
        await message.reply("✅ 请发送要绑定的 Bot Token，格式如：123456:ABCDEF...")

    @dp.message()
    async def handle_messages(message: Message):
        user_id = message.from_user.id
        state_key = USER_STATE_PREFIX + str(user_id)
        state = redis_client.get(state_key)

        logging.info(f"📩 捕获消息: 用户ID={user_id} | 状态={state} | 内容={message.text}")

        if state == "waiting_token":  # ✅ 修复这里
            token_input = message.text.strip()
            logging.info(f"📝 用户 [{user_id}] 提交 Token：{token_input}")

            redis_tokens = get_redis_tokens()

            if token_input in redis_tokens.values():
                await message.reply("⚠️ 该 Token 已绑定，请勿重复提交！")
                redis_client.delete(state_key)
                return

            existing_tokens = [
                name for name in redis_tokens.keys()
                if name == (message.from_user.username or f"user_{user_id}")
            ]
            if existing_tokens:
                await message.reply("⚠️ 你已绑定过一个 Bot，暂不支持绑定多个。")
                redis_client.delete(state_key)
                return

            test_bot = Bot(token=token_input)
            try:
                me = await test_bot.get_me()
                new_bot_name = message.from_user.username or f"user_{user_id}"
                await test_bot.session.close()

                redis_client.hset(REDIS_KEY, new_bot_name, token_input)
                await save_token_to_db(new_bot_name, token_input, user_id)

                await start_bot_func(new_bot_name, token_input)

                redis_client.delete(state_key)
                await message.reply(f"✅ Token 验证成功，已启动 🤖 @{me.username}")
            except Exception as e:
                await test_bot.session.close()
                logging.warning(f"❌ 用户 [{user_id}] 提交无效 Token: {e}")
                await message.reply("❌ Token 无效，请重新输入！")

    @dp.callback_query(lambda c: c.data.startswith("kb_text:"))
    async def handle_keyboard_text(callback: CallbackQuery):
        button_id = int(callback.data.split(":")[1])
        btn = await sync_to_async(BotKeyboardButton.objects.get)(id=button_id)
        await callback.message.answer(btn.action_value)
        await callback.answer()
