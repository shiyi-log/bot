from __future__ import annotations

import hashlib
import json
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from django.db import connection, transaction
from django.utils import timezone

from botcore.models import TronAddress, TronAlert, TronBlockCursor, TronTransferEvent

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
DEFAULT_USDT_CONTRACT = "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"

try:
    import fcntl
except ImportError:  # pragma: no cover - SQLite production is supported on Unix hosts.
    fcntl = None


def _base58_decode(value: str) -> bytes:
    number = 0
    for char in value:
        number = number * 58 + BASE58_ALPHABET.index(char)
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    return b"\x00" * (len(value) - len(value.lstrip("1"))) + raw


def is_valid_tron_address(address: str) -> bool:
    if len(address) != 34 or not address.startswith("T"):
        return False
    try:
        decoded = _base58_decode(address)
    except ValueError:
        return False
    if len(decoded) != 25 or decoded[0] != 0x41:
        return False
    payload, checksum = decoded[:-4], decoded[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return checksum == expected


@dataclass(frozen=True)
class TronSnapshot:
    balance_sun: int
    usdt_balance_sun: int = 0
    latest_transaction_id: str = ""
    resource_state: dict[str, Any] = field(default_factory=dict)
    permission_state: dict[str, Any] = field(default_factory=dict)


class TronProvider(Protocol):
    def get_snapshot(self, address: str) -> TronSnapshot: ...


def parse_tron_api_keys(raw: str) -> list[str]:
    parts = re.split(r"[\s,;，；]+", str(raw or "").strip())
    return list(dict.fromkeys(part for part in (item.strip() for item in parts) if part))


class TronGridProvider:
    """Read-only provider for public TRON account and transaction endpoints."""

    def __init__(self, api_url: str, api_key: str, usdt_contract: str = DEFAULT_USDT_CONTRACT):
        self.api_url = api_url.rstrip("/")
        self.api_keys = parse_tron_api_keys(api_key)
        self.usdt_contract = usdt_contract.strip() or DEFAULT_USDT_CONTRACT
        self._key_index = 0

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{self.api_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        keys = self.api_keys or [""]
        start = self._key_index % len(keys)
        self._key_index += 1
        for offset in range(len(keys)):
            key = keys[(start + offset) % len(keys)]
            headers = {"TRON-PRO-API-KEY": key} if key else {}
            request = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                if exc.code == 401 and offset < len(keys) - 1:
                    continue
                raise
        raise RuntimeError("TRON API request failed")

    def get_snapshot(self, address: str) -> TronSnapshot:
        account = self._get(f"/v1/accounts/{address}")
        account_rows = account.get("data") or []
        account_data = account_rows[0] if account_rows else {}
        balance = int(account_data.get("balance", 0) or 0)
        usdt_balance = 0
        for token in account_data.get("trc20") or []:
            if not isinstance(token, dict):
                continue
            for contract, value in token.items():
                if str(contract).lower() == self.usdt_contract.lower():
                    usdt_balance = int(value or 0)
                    break
        transactions = self._get(
            f"/v1/accounts/{address}/transactions",
            {"limit": "1", "order_by": "block_timestamp,desc", "only_confirmed": "true"},
        )
        rows = transactions.get("data") or []
        transaction_id = str(rows[0].get("txID", "")) if rows else ""
        resources = self._post("/wallet/getaccountresource", {"address": address, "visible": True})
        return TronSnapshot(
            balance_sun=balance,
            usdt_balance_sun=usdt_balance,
            latest_transaction_id=transaction_id,
            resource_state=normalize_tron_resource_state(resources),
            permission_state=normalize_account_permission_state(account_data),
        )

    def get_latest_block_number(self) -> int:
        payload = self._post("/wallet/getnowblock", {})
        return int(((payload.get("block_header") or {}).get("raw_data") or {}).get("number", 0))

    def get_block(self, number: int) -> dict[str, Any]:
        return self._post("/wallet/getblockbynum", {"num": number})

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.api_url}{path}"
        keys = self.api_keys or [""]
        start = self._key_index % len(keys)
        self._key_index += 1
        for offset in range(len(keys)):
            key = keys[(start + offset) % len(keys)]
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", **({"TRON-PRO-API-KEY": key} if key else {})},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                if exc.code == 401 and offset < len(keys) - 1:
                    continue
                raise
        raise RuntimeError("TRON API request failed")


def _hex_to_address(value: str) -> str:
    try:
        raw = bytes.fromhex(value.removeprefix("0x"))
    except ValueError:
        return ""
    if len(raw) == 20:
        raw = b"\x41" + raw
    if len(raw) != 21 or raw[0] != 0x41:
        return ""
    payload = raw
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    number = int.from_bytes(payload + checksum, "big")
    output = ""
    while number:
        number, remainder = divmod(number, 58)
        output = BASE58_ALPHABET[remainder] + output
    return "1" * (len(payload + checksum) - len((payload + checksum).lstrip(b"\0"))) + output


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalize_tron_resource_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Return stable account-only Energy/Bandwidth values for change detection."""

    energy_limit = _safe_int(payload.get("EnergyLimit"))
    energy_used = _safe_int(payload.get("EnergyUsed"))
    net_limit = _safe_int(payload.get("NetLimit"))
    net_used = _safe_int(payload.get("NetUsed"))
    free_net_limit = _safe_int(payload.get("freeNetLimit"))
    free_net_used = _safe_int(payload.get("freeNetUsed"))
    tron_power_limit = _safe_int(payload.get("tronPowerLimit"))
    tron_power_used = _safe_int(payload.get("tronPowerUsed"))

    def normalize_asset_map(value: Any) -> dict[str, int]:
        if not isinstance(value, dict):
            return {}
        return {str(key): _safe_int(item) for key, item in sorted(value.items(), key=lambda row: str(row[0]))}

    return {
        "energy_limit": energy_limit,
        "energy_used": energy_used,
        "energy_available": max(energy_limit - energy_used, 0),
        "net_limit": net_limit,
        "net_used": net_used,
        "free_net_limit": free_net_limit,
        "free_net_used": free_net_used,
        "bandwidth_available": max(net_limit + free_net_limit - net_used - free_net_used, 0),
        "tron_power_limit": tron_power_limit,
        "tron_power_used": tron_power_used,
        "asset_net_limit": normalize_asset_map(payload.get("assetNetLimit")),
        "asset_net_used": normalize_asset_map(payload.get("assetNetUsed")),
    }


def _normalize_permission(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    normalized = {
        "type": _normalize_permission_type(value.get("type")),
        "id": _safe_int(value.get("id")),
        "permission_name": str(value.get("permission_name", "")),
        "threshold": _safe_int(value.get("threshold")),
        "parent_id": _safe_int(value.get("parent_id")),
        "operations": str(value.get("operations", "")),
        "keys": [],
    }
    for key in value.get("keys") or []:
        if not isinstance(key, dict):
            continue
        raw_address = str(key.get("address", ""))
        normalized["keys"].append(
            {
                "address": _hex_to_address(raw_address) or raw_address,
                "weight": _safe_int(key.get("weight")),
            }
        )
    return normalized


def _normalize_permission_type(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    aliases = {
        "0": "Owner",
        "1": "Witness",
        "2": "Active",
        "owner": "Owner",
        "witness": "Witness",
        "active": "Active",
    }
    return aliases.get(text.lower(), text)


def normalize_permission_state(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "owner_permission": _normalize_permission(value.get("owner")),
        "witness_permission": _normalize_permission(value.get("witness")),
        "active_permissions": [
            _normalize_permission(permission)
            for permission in (value.get("actives") or [])
            if isinstance(permission, dict)
        ],
    }


def normalize_account_permission_state(value: dict[str, Any]) -> dict[str, Any]:
    if not any(key in value for key in ("owner_permission", "witness_permission", "active_permission")):
        return {}
    return normalize_permission_state(
        {
            "owner": value.get("owner_permission"),
            "witness": value.get("witness_permission"),
            "actives": value.get("active_permission"),
        }
    )


def _transaction_succeeded(tx: dict[str, Any]) -> bool:
    results = tx.get("ret") or []
    return bool(results) and all(str(item.get("contractRet", "")).upper() == "SUCCESS" for item in results)


@contextmanager
def _scanner_process_lock():
    """Serialize SQLite scanner processes; row locks cover other databases."""

    if connection.vendor != "sqlite":
        yield
        return
    if fcntl is None:
        raise RuntimeError("SQLite block scanning requires Unix file locking support.")
    database_name = str(connection.settings_dict.get("NAME", "default"))
    identity = hashlib.sha256(database_name.encode()).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"telegram-tron-bot-scanner-{identity}.lock"
    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def parse_block_transfers(block: dict[str, Any], block_number: int, usdt_contract: str = DEFAULT_USDT_CONTRACT) -> list[dict[str, Any]]:
    timestamp = ((block.get("block_header") or {}).get("raw_data") or {}).get("timestamp")
    block_time = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.get_current_timezone()) if timestamp else None
    events = []
    for tx in block.get("transactions") or []:
        if not _transaction_succeeded(tx):
            continue
        tx_id = str(tx.get("txID", ""))
        for index, contract in enumerate(((tx.get("raw_data") or {}).get("contract") or [])):
            value = contract.get("parameter", {}).get("value", {})
            if contract.get("type") == "TransferContract":
                from_address = _hex_to_address(str(value.get("owner_address", "")))
                to_address = _hex_to_address(str(value.get("to_address", "")))
                if from_address and to_address:
                    events.append({"block_number": block_number, "block_timestamp": block_time, "tx_id": tx_id, "event_index": index, "currency": "TRX", "contract_address": "", "from_address": from_address, "to_address": to_address, "amount_sun": int(value.get("amount", 0) or 0)})
            elif contract.get("type") == "TriggerSmartContract":
                data = str(value.get("data", ""))
                contract_address = _hex_to_address(str(value.get("contract_address", "")))
                if data.lower().startswith("a9059cbb") and len(data) >= 136 and contract_address.lower() == usdt_contract.lower():
                    to_address = _hex_to_address(data[32:72])
                    amount = int(data[72:136], 16)
                    from_address = _hex_to_address(str(value.get("owner_address", "")))
                    if from_address and to_address:
                        events.append({"block_number": block_number, "block_timestamp": block_time, "tx_id": tx_id, "event_index": index, "currency": "USDT", "contract_address": contract_address, "from_address": from_address, "to_address": to_address, "amount_sun": amount})
    return events


def parse_block_alerts(block: dict[str, Any], block_number: int) -> list[dict[str, Any]]:
    timestamp = ((block.get("block_header") or {}).get("raw_data") or {}).get("timestamp")
    block_time = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.get_current_timezone()) if timestamp else None
    alerts: list[dict[str, Any]] = []
    for tx in block.get("transactions") or []:
        if not _transaction_succeeded(tx):
            continue
        tx_id = str(tx.get("txID", ""))
        for index, contract in enumerate(((tx.get("raw_data") or {}).get("contract") or [])):
            value = contract.get("parameter", {}).get("value", {})
            contract_type = contract.get("type")
            if contract_type == "TriggerSmartContract":
                data = str(value.get("data", ""))
                if not data.lower().startswith("095ea7b3") or len(data) < 136:
                    continue
                owner_address = _hex_to_address(str(value.get("owner_address", "")))
                spender_address = _hex_to_address(data[32:72])
                contract_address = _hex_to_address(str(value.get("contract_address", "")))
                if not owner_address or not spender_address or not contract_address:
                    continue
                alerts.append(
                    {
                        "alert_type": TronAlert.Type.AUTHORIZATION_CHANGED,
                        "address_value": owner_address,
                        "block_number": block_number,
                        "block_timestamp": block_time,
                        "tx_id": tx_id,
                        "event_index": index,
                        "current_value": {
                            "contract_address": contract_address,
                            "owner_address": owner_address,
                            "spender_address": spender_address,
                            "amount_raw": str(int(data[72:136], 16)),
                        },
                    }
                )
            elif contract_type == "AccountPermissionUpdateContract":
                owner_address = _hex_to_address(str(value.get("owner_address", "")))
                if not owner_address:
                    continue
                alerts.append(
                    {
                        "alert_type": TronAlert.Type.PERMISSION_CHANGED,
                        "address_value": owner_address,
                        "block_number": block_number,
                        "block_timestamp": block_time,
                        "tx_id": tx_id,
                        "event_index": index,
                        "current_value": normalize_permission_state(value),
                    }
                )
    return alerts


def scan_blocks(provider: TronGridProvider, *, confirmations: int = 20, batch_size: int = 20) -> dict[str, int]:
    with _scanner_process_lock():
        return _scan_blocks_locked(provider, confirmations=confirmations, batch_size=batch_size)


def _scan_blocks_locked(provider: TronGridProvider, *, confirmations: int, batch_size: int) -> dict[str, int]:
    latest = provider.get_latest_block_number()
    target = latest - max(confirmations, 0)
    cursor, _ = TronBlockCursor.objects.get_or_create(network="mainnet")
    monitored = dict(TronAddress.objects.filter(enabled=True).values_list("address", "id"))
    result = {"latest": latest, "scanned": 0, "events": 0, "matched": 0, "alerts": 0}
    while result["scanned"] < max(batch_size, 1):
        with transaction.atomic():
            cursor = TronBlockCursor.objects.select_for_update().get(pk=cursor.pk)
            if cursor.next_block <= 0:
                cursor.next_block = max(0, target)
            if cursor.next_block > target:
                break
            number = cursor.next_block
            block = provider.get_block(number)
            events = parse_block_transfers(block, number, getattr(provider, "usdt_contract", DEFAULT_USDT_CONTRACT))
            for event in events:
                result["events"] += 1
                if event["from_address"] not in monitored and event["to_address"] not in monitored:
                    continue
                TronTransferEvent.objects.get_or_create(
                    tx_id=event["tx_id"],
                    event_index=event["event_index"],
                    defaults=event,
                )
                result["matched"] += 1
            for alert in parse_block_alerts(block, number):
                monitored_id = monitored.get(alert.pop("address_value"))
                if monitored_id is None:
                    continue
                monitored_address = TronAddress.objects.select_for_update().get(pk=monitored_id)
                previous_value: dict[str, Any] = {}
                if alert["alert_type"] == TronAlert.Type.PERMISSION_CHANGED:
                    previous_value = monitored_address.permission_snapshot or {}
                _, created = TronAlert.objects.get_or_create(
                    address=monitored_address,
                    alert_type=alert["alert_type"],
                    tx_id=alert["tx_id"],
                    event_index=alert["event_index"],
                    defaults={**alert, "previous_value": previous_value},
                )
                if created:
                    result["alerts"] += 1
                if (
                    alert["alert_type"] == TronAlert.Type.PERMISSION_CHANGED
                    and monitored_address.permission_snapshot != alert["current_value"]
                ):
                    monitored_address.permission_snapshot = alert["current_value"]
                    monitored_address.save(update_fields=["permission_snapshot", "updated_at"])
            cursor.last_scanned_block = number
            cursor.next_block = number + 1
            cursor.save(update_fields=["last_scanned_block", "next_block", "updated_at"])
        result["scanned"] += 1
    return result


def poll_enabled_addresses(provider: TronProvider) -> dict[str, int]:
    result = {"checked": 0, "updated": 0, "errors": 0}
    for monitored in TronAddress.objects.filter(enabled=True).iterator():
        result["checked"] += 1
        try:
            snapshot = provider.get_snapshot(monitored.address)
        except Exception as exc:  # provider failures are isolated per address
            monitored.status = TronAddress.Status.ERROR
            monitored.last_error = str(exc)[:1000]
            monitored.last_checked_at = timezone.now()
            monitored.save(update_fields=["status", "last_error", "last_checked_at", "updated_at"])
            result["errors"] += 1
            continue
        apply_snapshot(monitored, snapshot)
        result["updated"] += 1
    return result


def apply_snapshot(monitored: TronAddress, snapshot: TronSnapshot) -> TronAddress:
    previous_resources = monitored.resource_snapshot or {}
    current_resources = snapshot.resource_state or {}
    current_permissions = snapshot.permission_state or {}
    with transaction.atomic():
        if previous_resources and current_resources and previous_resources != current_resources:
            TronAlert.objects.create(
                address=monitored,
                alert_type=TronAlert.Type.RESOURCE_CHANGED,
                previous_value=previous_resources,
                current_value=current_resources,
            )
        monitored.balance_sun = snapshot.balance_sun
        monitored.usdt_balance_sun = snapshot.usdt_balance_sun
        if current_resources:
            monitored.resource_snapshot = current_resources
        if not monitored.permission_snapshot and current_permissions:
            monitored.permission_snapshot = current_permissions
        monitored.last_transaction_id = snapshot.latest_transaction_id
        monitored.status = TronAddress.Status.OK
        monitored.last_error = ""
        monitored.last_checked_at = timezone.now()
        monitored.save(update_fields=[
            "balance_sun", "usdt_balance_sun", "resource_snapshot", "permission_snapshot", "last_transaction_id", "status", "last_error", "last_checked_at", "updated_at",
        ])
    return monitored
