#!/usr/bin/env python
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("django_server.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'multibot.settings')
    import django
    django.setup()

    # ✅ 启动调度器
    from multibot.scheduler import start_scheduler
    start_scheduler()

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
