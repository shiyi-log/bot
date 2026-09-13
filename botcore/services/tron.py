from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Protocol

from django.utils import timezone

from botcore.models import TronAddress, TronBlockCursor, TronTransferEvent

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
DEFAULT_USDT_CONTRACT = "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"


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
        return TronSnapshot(
            balance_sun=balance,
            usdt_balance_sun=usdt_balance,
            latest_transaction_id=transaction_id,
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
    raw = bytes.fromhex(value.removeprefix("0x"))
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


def parse_block_transfers(block: dict[str, Any], block_number: int, usdt_contract: str = DEFAULT_USDT_CONTRACT) -> list[dict[str, Any]]:
    timestamp = ((block.get("block_header") or {}).get("raw_data") or {}).get("timestamp")
    block_time = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.get_current_timezone()) if timestamp else None
    events = []
    for tx in block.get("transactions") or []:
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


def scan_blocks(provider: TronGridProvider, *, confirmations: int = 20, batch_size: int = 20) -> dict[str, int]:
    latest = provider.get_latest_block_number()
    target = latest - max(confirmations, 0)
    cursor, _ = TronBlockCursor.objects.get_or_create(network="mainnet")
    if cursor.next_block <= 0:
        cursor.next_block = max(0, target)
    monitored = set(TronAddress.objects.filter(enabled=True).values_list("address", flat=True))
    result = {"latest": latest, "scanned": 0, "events": 0, "matched": 0}
    while cursor.next_block <= target and result["scanned"] < max(batch_size, 1):
        number = cursor.next_block
        events = parse_block_transfers(provider.get_block(number), number)
        for event in events:
            result["events"] += 1
            if event["from_address"] not in monitored and event["to_address"] not in monitored:
                continue
            TronTransferEvent.objects.get_or_create(tx_id=event["tx_id"], event_index=event["event_index"], defaults=event)
            result["matched"] += 1
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
    monitored.balance_sun = snapshot.balance_sun
    monitored.usdt_balance_sun = snapshot.usdt_balance_sun
    monitored.last_transaction_id = snapshot.latest_transaction_id
    monitored.status = TronAddress.Status.OK
    monitored.last_error = ""
    monitored.last_checked_at = timezone.now()
    monitored.save(update_fields=[
        "balance_sun", "usdt_balance_sun", "last_transaction_id", "status", "last_error", "last_checked_at", "updated_at",
    ])
    return monitored
