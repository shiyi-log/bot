from unittest.mock import patch
import urllib.error

from django.test import SimpleTestCase, TestCase

from botcore.models import TronAddress, TronAlert, TronBlockCursor, TronTransferEvent
from botcore.services.tron import (
    TronGridProvider,
    TronSnapshot,
    apply_snapshot,
    is_valid_tron_address,
    normalize_tron_resource_state,
    parse_tron_api_keys,
    parse_block_alerts,
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

    def test_resource_baseline_is_silent_then_change_creates_alert(self):
        monitored = TronAddress.objects.create(address=VALID_ADDRESS)
        initial = {
            "energy_limit": 100,
            "energy_used": 10,
            "energy_available": 90,
        }
        changed = {
            "energy_limit": 100,
            "energy_used": 25,
            "energy_available": 75,
        }
        baseline_permissions = {
            "owner_permission": {"threshold": 1, "keys": []},
            "witness_permission": {},
            "active_permissions": [],
        }
        apply_snapshot(monitored, TronSnapshot(
            balance_sun=1,
            resource_state=initial,
            permission_state=baseline_permissions,
        ))
        monitored.refresh_from_db()
        self.assertFalse(TronAlert.objects.exists())
        self.assertEqual(monitored.permission_snapshot, baseline_permissions)

        apply_snapshot(monitored, TronSnapshot(balance_sun=1, resource_state=changed))

        alert = TronAlert.objects.get()
        self.assertEqual(alert.alert_type, TronAlert.Type.RESOURCE_CHANGED)
        self.assertEqual(alert.previous_value, initial)
        self.assertEqual(alert.current_value, changed)


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
        account = {"data": [{
            "balance": 123,
            "trc20": [{provider.usdt_contract: "456"}],
            "owner_permission": {
                "type": 0,
                "id": 0,
                "permission_name": "owner",
                "threshold": 1,
                "keys": [{"address": "41" + "00" * 20, "weight": 1}],
            },
            "active_permission": [],
        }]}
        transactions = {"data": [{"txID": "tx-1"}]}
        resources = {"EnergyLimit": 100, "EnergyUsed": 40, "freeNetLimit": 600, "freeNetUsed": 20}
        with patch.object(provider, "_get", side_effect=[account, transactions]), patch.object(
            provider, "_post", return_value=resources
        ) as post:
            snapshot = provider.get_snapshot("T")
        self.assertEqual(snapshot.usdt_balance_sun, 456)
        self.assertEqual(snapshot.resource_state["energy_available"], 60)
        self.assertEqual(snapshot.resource_state["bandwidth_available"], 580)
        self.assertEqual(snapshot.permission_state["owner_permission"]["threshold"], 1)
        post.assert_called_once_with("/wallet/getaccountresource", {"address": "T", "visible": True})

    def test_resource_normalization_is_stable_and_account_scoped(self):
        normalized = normalize_tron_resource_state({
            "EnergyLimit": "10",
            "EnergyUsed": 3,
            "NetLimit": 5,
            "NetUsed": 2,
            "freeNetLimit": 7,
            "freeNetUsed": 1,
            "TotalEnergyLimit": 999,
            "assetNetUsed": {"2": "4", "1": 3},
        })
        self.assertEqual(normalized["energy_available"], 7)
        self.assertEqual(normalized["bandwidth_available"], 9)
        self.assertEqual(normalized["asset_net_used"], {"1": 3, "2": 4})
        self.assertNotIn("TotalEnergyLimit", normalized)

    def test_parse_block_transfers_handles_trx_and_usdt(self):
        owner = "41" + "00" * 20
        recipient = "41" + "00" * 19 + "01"
        contract = "41ea51342dabbb928ae1e576bd39eff8aaf070a8c6"
        block = {
            "block_header": {"raw_data": {"timestamp": 1700000000000}},
            "transactions": [
                {"txID": "trx-tx", "ret": [{"contractRet": "SUCCESS"}], "raw_data": {"contract": [{"type": "TransferContract", "parameter": {"value": {"owner_address": owner, "to_address": recipient, "amount": 9}}}]}},
                {"txID": "usdt-tx", "ret": [{"contractRet": "SUCCESS"}], "raw_data": {"contract": [{"type": "TriggerSmartContract", "parameter": {"value": {"owner_address": owner, "contract_address": contract, "data": "a9059cbb" + ("00" * 12) + recipient[2:] + ("00" * 31) + "07"}}}]}},
            ],
        }
        events = parse_block_transfers(block, 123)
        self.assertEqual([event["currency"] for event in events], ["TRX", "USDT"])
        self.assertEqual(events[1]["amount_sun"], 7)

    def test_parse_block_alerts_handles_approval_and_permission_update(self):
        owner = "41" + "00" * 20
        spender = "41" + "00" * 19 + "01"
        contract = "41" + "00" * 19 + "02"
        block = {
            "block_header": {"raw_data": {"timestamp": 1700000000000}},
            "transactions": [
                {
                    "txID": "approve-tx",
                    "ret": [{"contractRet": "SUCCESS"}],
                    "raw_data": {"contract": [{
                        "type": "TriggerSmartContract",
                        "parameter": {"value": {
                            "owner_address": owner,
                            "contract_address": contract,
                            "data": "095ea7b3" + ("00" * 12) + spender[2:] + ("00" * 31) + "09",
                        }},
                    }]},
                },
                {
                    "txID": "permission-tx",
                    "ret": [{"contractRet": "SUCCESS"}],
                    "raw_data": {"contract": [{
                        "type": "AccountPermissionUpdateContract",
                        "parameter": {"value": {
                            "owner_address": owner,
                            "owner": {
                                "type": 0,
                                "id": 0,
                                "permission_name": "owner",
                                "threshold": 2,
                                "keys": [{"address": spender, "weight": 1}],
                            },
                            "actives": [],
                        }},
                    }]},
                },
                {
                    "txID": "failed-approve",
                    "ret": [{"contractRet": "REVERT"}],
                    "raw_data": {"contract": [{
                        "type": "TriggerSmartContract",
                        "parameter": {"value": {
                            "owner_address": owner,
                            "contract_address": contract,
                            "data": "095ea7b3" + ("00" * 12) + spender[2:] + ("00" * 31) + "01",
                        }},
                    }]},
                },
            ],
        }

        alerts = parse_block_alerts(block, 123)

        self.assertEqual([alert["alert_type"] for alert in alerts], [
            TronAlert.Type.AUTHORIZATION_CHANGED,
            TronAlert.Type.PERMISSION_CHANGED,
        ])
        self.assertEqual(alerts[0]["current_value"]["amount_raw"], "9")
        self.assertEqual(alerts[1]["current_value"]["owner_permission"]["threshold"], 2)
        self.assertEqual(alerts[1]["current_value"]["owner_permission"]["type"], "Owner")

    def test_block_parsers_require_explicit_success_result(self):
        owner = "41" + "00" * 20
        recipient = "41" + "00" * 19 + "01"
        contract = "41" + "00" * 19 + "02"
        block = {"transactions": [{
            "txID": "unknown-result",
            "raw_data": {"contract": [
                {"type": "TransferContract", "parameter": {"value": {
                    "owner_address": owner,
                    "to_address": recipient,
                    "amount": 1,
                }}},
                {"type": "TriggerSmartContract", "parameter": {"value": {
                    "owner_address": owner,
                    "contract_address": contract,
                    "data": "095ea7b3" + ("00" * 12) + recipient[2:] + ("00" * 31) + "01",
                }}},
            ]},
        }]}

        self.assertEqual(parse_block_transfers(block, 1), [])
        self.assertEqual(parse_block_alerts(block, 1), [])


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

    def test_scan_blocks_saves_chain_alerts_idempotently(self):
        monitored = TronAddress.objects.create(address=VALID_ADDRESS)
        owner = "41" + "00" * 20
        spender = "41" + "00" * 19 + "01"
        contract = "41" + "00" * 19 + "02"
        block = {
            "transactions": [
                {"txID": "approve", "ret": [{"contractRet": "SUCCESS"}], "raw_data": {"contract": [{
                    "type": "TriggerSmartContract",
                    "parameter": {"value": {
                        "owner_address": owner,
                        "contract_address": contract,
                        "data": "095ea7b3" + ("00" * 12) + spender[2:] + ("00" * 31) + "05",
                    }},
                }]}},
                {"txID": "permissions", "ret": [{"contractRet": "SUCCESS"}], "raw_data": {"contract": [{
                    "type": "AccountPermissionUpdateContract",
                    "parameter": {"value": {
                        "owner_address": owner,
                        "owner": {"threshold": 1, "keys": [{"address": owner, "weight": 1}]},
                        "actives": [],
                    }},
                }]}},
            ],
        }

        class FakeBlockProvider:
            usdt_contract = ""

            def get_latest_block_number(self):
                return 100

            def get_block(self, number):
                return block

        cursor = TronBlockCursor.objects.create(network="mainnet", next_block=100)
        first = scan_blocks(FakeBlockProvider(), confirmations=0, batch_size=1)
        self.assertEqual(first["alerts"], 2)
        self.assertEqual(TronAlert.objects.count(), 2)

        cursor.next_block = 100
        cursor.last_scanned_block = 99
        cursor.save(update_fields=["next_block", "last_scanned_block", "updated_at"])
        second = scan_blocks(FakeBlockProvider(), confirmations=0, batch_size=1)

        monitored.refresh_from_db()
        self.assertEqual(second["alerts"], 0)
        self.assertEqual(TronAlert.objects.count(), 2)
        self.assertEqual(monitored.permission_snapshot["owner_permission"]["threshold"], 1)

    def test_scan_block_rolls_back_events_and_cursor_on_parser_error(self):
        TronAddress.objects.create(address=VALID_ADDRESS)
        owner = "41" + "00" * 20
        recipient = "41" + "00" * 19 + "01"
        contract = "41" + "00" * 19 + "02"
        block = {
            "transactions": [
                {"txID": "transfer", "ret": [{"contractRet": "SUCCESS"}], "raw_data": {"contract": [{
                    "type": "TransferContract",
                    "parameter": {"value": {"owner_address": owner, "to_address": recipient, "amount": 1}},
                }]}},
                {"txID": "bad-approve", "ret": [{"contractRet": "SUCCESS"}], "raw_data": {"contract": [{
                    "type": "TriggerSmartContract",
                    "parameter": {"value": {
                        "owner_address": owner,
                        "contract_address": contract,
                        "data": "095ea7b3" + ("00" * 12) + recipient[2:] + ("zz" * 32),
                    }},
                }]}},
            ],
        }

        class BrokenBlockProvider:
            def get_latest_block_number(self):
                return 100

            def get_block(self, number):
                return block

        cursor = TronBlockCursor.objects.create(network="mainnet", next_block=100)
        with self.assertRaises(ValueError):
            scan_blocks(BrokenBlockProvider(), confirmations=0, batch_size=1)

        cursor.refresh_from_db()
        self.assertEqual(cursor.next_block, 100)
        self.assertEqual(cursor.last_scanned_block, 0)
        self.assertFalse(TronTransferEvent.objects.exists())
        self.assertFalse(TronAlert.objects.exists())
