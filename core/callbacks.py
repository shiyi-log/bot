import logging
from aiogram import Dispatcher
from aiogram.types import CallbackQuery
from core.redis_utils import redis_client, BLOCK_PREFIX

def register_global_callbacks(dp: Dispatcher):
    """
    注册全局回调处理器，用于处理“屏蔽用户”操作。
    """
    logging.info("🔧 已注册全局回调处理器：支持屏蔽用户功能")

    @dp.callback_query(lambda c: c.data and c.data.startswith("block:"))
    async def handle_block_user(callback: CallbackQuery):
        """
        处理点击“屏蔽用户 10 分钟”按钮的回调事件。
        回调数据格式: block:<bot_name>:<user_id>
        """
        logging.info(f"📥 收到屏蔽请求: {callback.data} | 操作者ID: {callback.from_user.id}")

        try:
            # 解析回调数据
            _, bot_name, target_user_id = callback.data.split(":")
            redis_key = f"{BLOCK_PREFIX}:{bot_name}:{target_user_id}"

            # 设置屏蔽标志（10分钟）
            redis_client.setex(redis_key, 600, "1")

            # 反馈消息
            await callback.answer("🚫 已屏蔽该用户 10 分钟")
            logging.info(f"✅ 屏蔽成功: {redis_key} 设置 600 秒")

        except ValueError:
            logging.error(f"❌ 回调参数格式错误: {callback.data}")
            await callback.answer("⚠️ 参数格式错误，无法处理")

        except Exception as e:
            logging.exception(f"❌ 屏蔽操作失败: {e}")
            await callback.answer("⚠️ 操作失败，请稍后再试")
