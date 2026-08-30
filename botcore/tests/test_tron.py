from unittest.mock import patch
import urllib.error

from django.test import SimpleTestCase, TestCase

from botcore.models import TronAddress
from botcore.services.tron import (
    TronGridProvider,
    TronSnapshot,
    is_valid_tron_address,
    parse_tron_api_keys,
    poll_enabled_addresses,
)

VALID_ADDRESS = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"


class FakeProvider:
    def get_snapshot(self, address):
        return TronSnapshot(balance_sun=1_500_000, usdt_balance_sun=2_500_000, latest_transaction_id="tx-123")


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
        self.assertEqual(monitored.usdt_balance_sun, 2_500_000)
        self.assertEqual(monitored.last_transaction_id, "tx-123")
        self.assertEqual(monitored.status, TronAddress.Status.OK)

    def test_provider_error_is_recorded_per_address(self):
        monitored = TronAddress.objects.create(address=VALID_ADDRESS)
        result = poll_enabled_addresses(FailingProvider())
        monitored.refresh_from_db()
        self.assertEqual(result["errors"], 1)
        self.assertEqual(monitored.status, TronAddress.Status.ERROR)
        self.assertIn("provider unavailable", monitored.last_error)


class TronProviderTests(SimpleTestCase):
    def test_parse_api_keys_accepts_common_separators_and_deduplicates(self):
        self.assertEqual(
            parse_tron_api_keys(" alpha\nbeta,alpha； gamma; beta "),
            ["alpha", "beta", "gamma"],
        )

    def test_401_rotates_to_next_key(self):
        provider = TronGridProvider("https://api.trongrid.io", "first\nsecond")

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"ok": true}'

        calls = []

        def fake_urlopen(request, timeout):
            calls.append(request.get_header("Tron-pro-api-key"))
            if len(calls) == 1:
                raise urllib.error.HTTPError(request.full_url, 401, "unauthorized", {}, None)
            return Response()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(provider._get("/v1/accounts/T"), {"ok": True})

        self.assertEqual(calls, ["first", "second"])

    def test_snapshot_extracts_usdt_from_trc20(self):
        provider = TronGridProvider("https://api.trongrid.io", "key")
        account = {"data": [{"balance": 123, "trc20": [{provider.usdt_contract: "456"}]}]}
        transactions = {"data": [{"txID": "tx-1"}]}
        with patch.object(provider, "_get", side_effect=[account, transactions]):
            snapshot = provider.get_snapshot("T")
        self.assertEqual(snapshot.usdt_balance_sun, 456)
