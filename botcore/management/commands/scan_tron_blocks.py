import os
import time

from django.core.management.base import BaseCommand, CommandError

from botcore.models import BotSettings
from botcore.services.tron import TronGridProvider, scan_blocks


class Command(BaseCommand):
    help = "Scan confirmed TRON blocks and store read-only transfer events."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--confirmations", type=int, default=20)
        parser.add_argument("--batch-size", type=int, default=20)

    def handle(self, *args, **options):
        if os.getenv("ENABLE_TRON_NETWORK", "0") != "1":
            raise CommandError("TRON network is disabled; set ENABLE_TRON_NETWORK=1 explicitly.")
        settings = BotSettings.load()
        api_key = settings.tron_api_key.strip() or os.getenv(settings.tron_api_key_env_var, "").strip()
        if not api_key:
            raise CommandError(f"{settings.tron_api_key_env_var} is required.")
        provider = TronGridProvider(settings.tron_api_url, api_key, os.getenv("TRON_USDT_CONTRACT", ""))
        while True:
            result = scan_blocks(provider, confirmations=options["confirmations"], batch_size=options["batch_size"])
            self.stdout.write(str(result))
            if options["once"]:
                return
            time.sleep(settings.tron_poll_interval or 30)
