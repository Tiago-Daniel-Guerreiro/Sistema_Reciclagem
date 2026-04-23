import base64
import hashlib
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

LEGACY_FERNET_KEY = b"yjqbeqH_w0LJkt817PUpjkCXN-3sqgysBttLSjawWqo="
LEGACY_CIPHER = Fernet(LEGACY_FERNET_KEY)


def _load_aes_key() -> bytes:
    key_b64 = os.getenv("SECURITY_AES_KEY_B64")
    if key_b64:
        padding = "=" * (-len(key_b64) % 4)
        key = base64.urlsafe_b64decode((key_b64 + padding).encode("utf-8"))
        if len(key) not in (16, 24, 32):
            raise ValueError("SECURITY_AES_KEY_B64 deve decodificar para 16/24/32 bytes")
        return key

    return hashlib.sha256(LEGACY_FERNET_KEY).digest()


AES_KEY = _load_aes_key()
AES_CIPHER = AESGCM(AES_KEY)
AES_PREFIX = "aesgcm$"


def encrypt_password(password: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AES_CIPHER.encrypt(nonce, password.encode("utf-8"), None)
    payload = base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")
    return f"{AES_PREFIX}{payload}"


def decrypt_password(encrypted_password: str) -> str:
    if encrypted_password.startswith(AES_PREFIX):
        payload_b64 = encrypted_password[len(AES_PREFIX):]
        padding = "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode((payload_b64 + padding).encode("utf-8"))
        nonce = payload[:12]
        ciphertext = payload[12:]
        plain = AES_CIPHER.decrypt(nonce, ciphertext, None)
        return plain.decode("utf-8")

    return LEGACY_CIPHER.decrypt(encrypted_password.encode("utf-8")).decode("utf-8")


def verify_password(plain_password: str, encrypted_password: str) -> bool:
    try:
        decrypted = decrypt_password(encrypted_password)
        return plain_password == decrypted
    except Exception:
        return False