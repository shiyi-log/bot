from unittest.mock import patch
import urllib.error

from django.test import SimpleTestCase, TestCase

from botcore.models import TronAddress, TronBlockCursor, TronTransferEvent
from botcore.services.tron import (
    TronGridProvider,
    TronSnapshot,
    is_valid_tron_address,
    parse_tron_api_keys,
    poll_enabled_addresses,
    parse_block_transfers,
    scan_blocks,
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

    def test_parse_block_transfers_handles_trx_and_usdt(self):
        owner = "41" + "00" * 20
        recipient = "41" + "00" * 19 + "01"
        contract = "41ea51342dabbb928ae1e576bd39eff8aaf070a8c6"
        block = {
            "block_header": {"raw_data": {"timestamp": 1700000000000}},
            "transactions": [
                {"txID": "trx-tx", "raw_data": {"contract": [{"type": "TransferContract", "parameter": {"value": {"owner_address": owner, "to_address": recipient, "amount": 9}}}]}},
                {"txID": "usdt-tx", "raw_data": {"contract": [{"type": "TriggerSmartContract", "parameter": {"value": {"owner_address": owner, "contract_address": contract, "data": "a9059cbb" + ("00" * 12) + recipient[2:] + ("00" * 31) + "07"}}}]}},
            ],
        }
        events = parse_block_transfers(block, 123)
        self.assertEqual([event["currency"] for event in events], ["TRX", "USDT"])
        self.assertEqual(events[1]["amount_sun"], 7)


class TronBlockScannerTests(TestCase):
    def test_scan_blocks_advances_cursor_and_deduplicates_matching_events(self):
        monitored = TronAddress.objects.create(address=VALID_ADDRESS)

        class FakeBlockProvider:
            def get_latest_block_number(self):
                return 105

            def get_block(self, number):
                return {"transactions": []}

        cursor = TronBlockCursor.objects.create(network="mainnet", next_block=100)
        result = scan_blocks(FakeBlockProvider(), confirmations=2, batch_size=10)
        cursor.refresh_from_db()
        self.assertEqual(result["scanned"], 4)
        self.assertEqual(cursor.next_block, 104)
        self.assertEqual(TronTransferEvent.objects.count(), 0)
