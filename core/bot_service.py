import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError

from core.middleware import LoggingAndForwardMiddleware
from core.callbacks import register_global_callbacks
from core.commands import register_bot_commands
from core.redis_utils import redis_client, REDIS_RUNNING_KEY

# 正在运行的 Bot 实例及其轮询任务记录
running_bots: dict[str, dict] = {}

# ===== 启动 Bot =====
async def start_bot(bot_name: str, token: str):
    """
    启动指定名称和 Token 的 Bot 实例，并注册中间件、回调和指令。
    防止重复启动，成功后记录到 running_bots。
    """
    if redis_client.hexists(REDIS_RUNNING_KEY, bot_name):
       # logging.warning(f"⚠️ [Bot:{bot_name}] 已运行，跳过重复启动")
        return

    redis_client.hset(REDIS_RUNNING_KEY, bot_name, "running")

    bot = Bot(token=token)
    dp = Dispatcher()

    # 中间件 / 回调 / 指令注册
    dp.message.middleware(LoggingAndForwardMiddleware())
    register_global_callbacks(dp)
    register_bot_commands(dp, bot_name, bot, start_bot_func=start_bot)

    # 添加上下文信息
    dp.workflow_data.update({
        "bot_name": bot_name,
        "bot": bot,
    })

    try:
        # 异步启动轮询监听
        task = asyncio.create_task(dp.start_polling(bot), name=f"bot:{bot_name}")
        running_bots[bot_name] = {"bot": bot, "task": task}

        me = await bot.get_me()
        logging.info(f"✅ 启动成功 [Bot:{bot_name}] | 昵称: {me.first_name} | 用户名: @{me.username}")

    except TelegramAPIError as e:
        logging.error(f"❌ 启动失败 [Bot:{bot_name}] | 错误: {e}")
        redis_client.hdel(REDIS_RUNNING_KEY, bot_name)
        await bot.session.close()

# ===== 停止 Bot =====
async def stop_bot(bot_name: str):
    """
    停止指定 Bot 实例：
    - 关闭 Bot 会话；
    - 取消监听任务；
    - 清除 Redis 标记。
    """
    if bot_name in running_bots:
        bot_entry = running_bots.pop(bot_name)

        await bot_entry["bot"].session.close()
        bot_entry["task"].cancel()

        redis_client.hdel(REDIS_RUNNING_KEY, bot_name)
        logging.info(f"🛑 已停止 Bot：{bot_name}")
    else:
        logging.warning(f"⚠️ 无需停止，Bot [{bot_name}] 当前未运行")
