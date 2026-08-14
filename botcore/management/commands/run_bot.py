import os
import time

from django.core.management.base import BaseCommand, CommandError

from botcore.models import BotSettings
from botcore.services.telegram import TelegramBotAPITransport, handle_update


class Command(BaseCommand):
    help = "Run Telegram long polling (network access is disabled by default)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Fetch one update batch and exit.")

    def handle(self, *args, **options):
        if os.getenv("ENABLE_TELEGRAM_NETWORK", "0") != "1":
            raise CommandError("Telegram network is disabled; set ENABLE_TELEGRAM_NETWORK=1 explicitly.")
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN is required.")
        if not BotSettings.load().bot_enabled:
            raise CommandError("Bot is disabled in settings.")

        timeout = max(1, int(os.getenv("TELEGRAM_POLL_TIMEOUT", "30")))
        transport = TelegramBotAPITransport(token)
        offset = None
        self.stdout.write("Telegram polling started.")
        while True:
            try:
                updates = transport.get_updates(offset=offset, timeout=timeout)
                for update in updates:
                    handle_update(update, transport)
                    offset = int(update["update_id"]) + 1
            except KeyboardInterrupt:
                self.stdout.write("Telegram polling stopped.")
                return
            except Exception as exc:
                self.stderr.write(f"Telegram polling error: {exc}")
                if options["once"]:
                    raise CommandError("Telegram polling failed.") from exc
                time.sleep(5)
            if options["once"]:
                return
