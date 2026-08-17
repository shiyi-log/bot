from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from django.utils import timezone

from botcore.models import TronAddress

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


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
    latest_transaction_id: str = ""


class TronProvider(Protocol):
    def get_snapshot(self, address: str) -> TronSnapshot: ...


def parse_tron_api_keys(raw: str) -> list[str]:
    parts = re.split(r"[\s,;，；]+", str(raw or "").strip())
    return list(dict.fromkeys(part for part in (item.strip() for item in parts) if part))


class TronGridProvider:
    """Read-only provider for public TRON account and transaction endpoints."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_keys = parse_tron_api_keys(api_key)
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
        balance = int(account_rows[0].get("balance", 0)) if account_rows else 0
        transactions = self._get(
            f"/v1/accounts/{address}/transactions",
            {"limit": "1", "order_by": "block_timestamp,desc", "only_confirmed": "true"},
        )
        rows = transactions.get("data") or []
        transaction_id = str(rows[0].get("txID", "")) if rows else ""
        return TronSnapshot(balance_sun=balance, latest_transaction_id=transaction_id)


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
        monitored.balance_sun = snapshot.balance_sun
        monitored.last_transaction_id = snapshot.latest_transaction_id
        monitored.status = TronAddress.Status.OK
        monitored.last_error = ""
        monitored.last_checked_at = timezone.now()
        monitored.save(update_fields=[
            "balance_sun", "last_transaction_id", "status", "last_error", "last_checked_at", "updated_at",
        ])
        result["updated"] += 1
    return result
