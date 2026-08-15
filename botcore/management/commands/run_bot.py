import os
import threading

from django.core.management.base import BaseCommand, CommandError

from botcore.models import TelegramBot
from botcore.services.telegram import TelegramBotAPITransport, handle_update


class Command(BaseCommand):
    help = "Run one or more Telegram bots (network access is disabled by default)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Fetch one update batch per bot and exit.")
        parser.add_argument(
            "--bot-id",
            action="append",
            type=int,
            dest="bot_ids",
            help="Run only this enabled bot. Repeat to select multiple bots.",
        )

    def _load_bots(self, bot_ids: list[int] | None) -> list[tuple[TelegramBot, str]]:
        queryset = TelegramBot.objects.filter(enabled=True)
        if bot_ids:
            queryset = queryset.filter(id__in=bot_ids)
        bots = list(queryset.order_by("id"))
        if bot_ids and len(bots) != len(set(bot_ids)):
            found = {bot.id for bot in bots}
            missing = sorted(set(bot_ids) - found)
            raise CommandError(f"Enabled Telegram bot not found: {', '.join(map(str, missing))}.")
        if not bots:
            raise CommandError("No enabled Telegram bots are configured.")

        configured: list[tuple[TelegramBot, str]] = []
        for bot in bots:
            token = os.getenv(bot.token_env_var, "").strip()
            if token:
                configured.append((bot, token))
            else:
                self.stderr.write(
                    self.style.WARNING(
                        f"Skipping bot {bot.id} ({bot.name}): {bot.token_env_var} is not configured."
                    )
                )
        if not configured:
            raise CommandError("No enabled Telegram bot has a configured token environment variable.")
        return configured

    def _poll_once(self, bot: TelegramBot, token: str, timeout: int) -> None:
        transport = TelegramBotAPITransport(token)
        for update in transport.get_updates(offset=None, timeout=timeout):
            handle_update(update, transport, bot=bot)

    def _poll_forever(
        self,
        bot: TelegramBot,
        token: str,
        timeout: int,
        stop_event: threading.Event,
    ) -> None:
        transport = TelegramBotAPITransport(token)
        offset = None
        while not stop_event.is_set():
            try:
                updates = transport.get_updates(offset=offset, timeout=timeout)
                for update in updates:
                    handle_update(update, transport, bot=bot)
                    offset = int(update["update_id"]) + 1
            except Exception as exc:
                self.stderr.write(
                    f"Telegram polling error for bot {bot.id} ({bot.name}): "
                    f"{type(exc).__name__}"
                )
                stop_event.wait(5)

    def handle(self, *args, **options):
        if os.getenv("ENABLE_TELEGRAM_NETWORK", "0") != "1":
            raise CommandError("Telegram network is disabled; set ENABLE_TELEGRAM_NETWORK=1 explicitly.")

        bots = self._load_bots(options["bot_ids"])
        timeout = max(1, int(os.getenv("TELEGRAM_POLL_TIMEOUT", "30")))
        self.stdout.write(f"Telegram polling started for {len(bots)} bot(s).")

        if options["once"]:
            try:
                for bot, token in bots:
                    self._poll_once(bot, token, timeout)
            except Exception as exc:
                raise CommandError("Telegram polling failed.") from exc
            return

        stop_event = threading.Event()
        threads = [
            threading.Thread(
                target=self._poll_forever,
                args=(bot, token, timeout, stop_event),
                name=f"telegram-bot-{bot.id}",
                daemon=True,
            )
            for bot, token in bots
        ]
        for thread in threads:
            thread.start()
        try:
            while any(thread.is_alive() for thread in threads):
                for thread in threads:
                    thread.join(timeout=0.5)
        except KeyboardInterrupt:
            self.stdout.write("Telegram polling stopped.")
        finally:
            stop_event.set()
            for thread in threads:
                thread.join(timeout=timeout + 2)
