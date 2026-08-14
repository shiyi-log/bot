from django.test import TestCase

from botcore.models import TronAddress
from botcore.services.tron import TronSnapshot, is_valid_tron_address, poll_enabled_addresses

VALID_ADDRESS = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"


class FakeProvider:
    def get_snapshot(self, address):
        return TronSnapshot(balance_sun=1_500_000, latest_transaction_id="tx-123")


class FailingProvider:
    def get_snapshot(self, address):
        raise RuntimeError("provider unavailable")


class TronMonitorTests(TestCase):
    def test_address_validation(self):
        self.assertTrue(is_valid_tron_address(VALID_ADDRESS))
        self.assertFalse(is_valid_tron_address("T" + "x" * 33))

    def test_poll_updates_balance_and_latest_transaction_without_network(self):
        monitored = TronAddress.objects.create(address=VALID_ADDRESS)
        result = poll_enabled_addresses(FakeProvider())
        monitored.refresh_from_db()
        self.assertEqual(result, {"checked": 1, "updated": 1, "errors": 0})
        self.assertEqual(monitored.balance_sun, 1_500_000)
        self.assertEqual(monitored.last_transaction_id, "tx-123")
        self.assertEqual(monitored.status, TronAddress.Status.OK)

    def test_provider_error_is_recorded_per_address(self):
        monitored = TronAddress.objects.create(address=VALID_ADDRESS)
        result = poll_enabled_addresses(FailingProvider())
        monitored.refresh_from_db()
        self.assertEqual(result["errors"], 1)
        self.assertEqual(monitored.status, TronAddress.Status.ERROR)
        self.assertIn("provider unavailable", monitored.last_error)
