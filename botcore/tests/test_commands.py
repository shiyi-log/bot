from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from botcore.models import TelegramBot


class FailClosedCommandTests(TestCase):
    @patch.dict("os.environ", {"ENABLE_TELEGRAM_NETWORK": "0"}, clear=False)
    def test_run_bot_rejects_network_by_default(self):
        with self.assertRaisesMessage(CommandError, "Telegram network is disabled"):
            call_command("run_bot", "--once", stdout=StringIO())

    @patch.dict("os.environ", {"ENABLE_TRON_NETWORK": "0"}, clear=False)
    def test_monitor_tron_rejects_network_by_default(self):
        with self.assertRaisesMessage(CommandError, "TRON network is disabled"):
            call_command("monitor_tron", "--once", stdout=StringIO())

    @patch.dict("os.environ", {"ENABLE_TRON_NETWORK": "0"}, clear=False)
    def test_scan_tron_blocks_rejects_network_by_default(self):
        with self.assertRaisesMessage(CommandError, "TRON network is disabled"):
            call_command("scan_tron_blocks", "--once", stdout=StringIO())

    @patch("botcore.management.commands.run_bot.TelegramBotAPITransport")
    @patch.dict("os.environ", {
        "ENABLE_TELEGRAM_NETWORK": "1",
        "MAIN_BOT_TOKEN": "test-main-token",
        "SUPPORT_BOT_TOKEN": "test-support-token",
    }, clear=False)
    def test_run_bot_once_polls_each_enabled_configured_bot(self, transport_class):
        TelegramBot.objects.create(name="Main", token_env_var="MAIN_BOT_TOKEN", enabled=True)
        TelegramBot.objects.create(name="Support", token_env_var="SUPPORT_BOT_TOKEN", enabled=True)
        transport_class.return_value.get_updates.return_value = []

        call_command("run_bot", "--once", stdout=StringIO())

        self.assertEqual(transport_class.call_count, 2)
        self.assertEqual(transport_class.return_value.get_updates.call_count, 2)
