# bots/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path("heartbeat/", views.heartbeat, name="heartbeat"),
    path("assigned-bots/", views.assigned_bots, name="assigned_bots"),
    path("register-bot/", views.register_bot, name="register_bot"),
    path("reassign-bots/", views.reassign_all_bots, name="reassign_all_bots"),
    path("all-tokens/", views.all_tokens),  # 👈 加这行
    path("all-status/", views.all_bot_status),  # ✅ 新增调试接口
    path("system-status/", views.system_status),  # ⬅️ 添加这一行
    path("api/", include("bots.urls")),  # ⬅️ 确保你这行包含了 bots.urls

]
