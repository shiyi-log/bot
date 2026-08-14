from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class FailClosedCommandTests(TestCase):
    @patch.dict("os.environ", {"ENABLE_TELEGRAM_NETWORK": "0"}, clear=False)
    def test_run_bot_rejects_network_by_default(self):
        with self.assertRaisesMessage(CommandError, "Telegram network is disabled"):
            call_command("run_bot", "--once", stdout=StringIO())

    @patch.dict("os.environ", {"ENABLE_TRON_NETWORK": "0"}, clear=False)
    def test_monitor_tron_rejects_network_by_default(self):
        with self.assertRaisesMessage(CommandError, "TRON network is disabled"):
            call_command("monitor_tron", "--once", stdout=StringIO())
