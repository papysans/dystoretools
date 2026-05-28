from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from dystore.core.config import get_settings


class EncryptionKeyMissing(RuntimeError):
    pass


def _master_key() -> bytes:
    value = get_settings().chat_master_encryption_key
    if not value:
        raise EncryptionKeyMissing("CHAT_MASTER_ENCRYPTION_KEY is required for provider API keys")
    return base64.b64decode(value, validate=True)


def encrypt_secret(value: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_master_key()).encrypt(nonce, value.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_secret(value: str) -> str:
    raw = base64.b64decode(value, validate=True)
    nonce, ciphertext = raw[:12], raw[12:]
    return AESGCM(_master_key()).decrypt(nonce, ciphertext, None).decode("utf-8")


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]


def fingerprint_secret(value: str | None) -> str | None:
    if not value:
        return None
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:16]
