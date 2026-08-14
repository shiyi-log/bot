import os
import time

from django.core.management.base import BaseCommand, CommandError

from botcore.models import BotSettings
from botcore.services.tron import TronGridProvider, poll_enabled_addresses


class Command(BaseCommand):
    help = "Poll configured TRON addresses using read-only TRONGrid endpoints."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Poll once and exit.")

    def handle(self, *args, **options):
        if os.getenv("ENABLE_TRON_NETWORK", "0") != "1":
            raise CommandError("TRON network is disabled; set ENABLE_TRON_NETWORK=1 explicitly.")
        api_key = os.getenv("TRONGRID_API_KEY", "").strip()
        if not api_key:
            raise CommandError("TRONGRID_API_KEY is required.")
        settings = BotSettings.load()
        if not settings.tron_monitor_enabled:
            raise CommandError("TRON monitoring is disabled in settings.")

        provider = TronGridProvider(os.getenv("TRONGRID_API_URL", "https://api.trongrid.io"), api_key)
        interval = settings.tron_poll_interval or max(5, int(os.getenv("TRON_POLL_INTERVAL", "30")))
        self.stdout.write("TRON monitoring started.")
        while True:
            result = poll_enabled_addresses(provider)
            self.stdout.write(
                f"checked={result['checked']} updated={result['updated']} errors={result['errors']}"
            )
            if options["once"]:
                return
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write("TRON monitoring stopped.")
                return
