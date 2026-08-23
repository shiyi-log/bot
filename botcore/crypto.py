import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


FERNET_PREFIX = "fernet:"


def _fernet() -> Fernet:
    source_key = getattr(settings, "CONFIG_ENCRYPTION_KEY", "") or settings.SECRET_KEY
    digest = hashlib.sha256(str(source_key).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_text(value: str) -> str:
    if not value or value.startswith(FERNET_PREFIX):
        return value
    token = _fernet().encrypt(value.encode()).decode()
    return f"{FERNET_PREFIX}{token}"


def decrypt_text(value: str, *, allow_plaintext: bool = False) -> str:
    if not value:
        return value
    if not value.startswith(FERNET_PREFIX):
        return value if allow_plaintext else ""
    token = value.removeprefix(FERNET_PREFIX)
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError, UnicodeDecodeError):
        return ""
