from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Worker, Bot

@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ("machine_id", "last_heartbeat", "is_alive")

@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ("name", "assigned_worker", "created_at")
