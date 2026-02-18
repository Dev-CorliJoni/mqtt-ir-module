import base64
import hashlib
import os
from typing import Optional, Tuple


class SettingsCipher:
    def __init__(self, master_key: str) -> None:
        self._master_key = (master_key or "").strip()
        self._resolved_key = self._resolve_key(self._master_key)

    @property
    def is_configured(self) -> bool:
        return self._resolved_key is not None

    def encrypt(self, plaintext: str) -> Tuple[str, str]:
        if plaintext is None:
            raise ValueError("plaintext must not be None")

        key = self._require_key()
        nonce = os.urandom(12)
        aesgcm = self._new_aesgcm(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return self._encode_b64(ciphertext), self._encode_b64(nonce)

    def decrypt(self, ciphertext_b64: str, nonce_b64: str) -> str:
        key = self._require_key()
        ciphertext = self._decode_b64(ciphertext_b64)
        nonce = self._decode_b64(nonce_b64)
        aesgcm = self._new_aesgcm(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")

    def _require_key(self) -> bytes:
        if self._resolved_key is None:
            raise ValueError("settings_master_key_missing")
        return self._resolved_key

    def _resolve_key(self, raw: str) -> Optional[bytes]:
        if not raw:
            return None
        decoded = self._decode_optional_b64_key(raw)
        if decoded is not None:
            return decoded
        return hashlib.sha256(raw.encode("utf-8")).digest()

    def _decode_optional_b64_key(self, raw: str) -> Optional[bytes]:
        normalized = raw.strip()
        if not normalized:
            return None

        pad = "=" * ((4 - (len(normalized) % 4)) % 4)
        try:
            decoded = base64.urlsafe_b64decode((normalized + pad).encode("ascii"))
        except Exception:
            return None

        if len(decoded) not in (16, 24, 32):
            return None
        return decoded

    def _new_aesgcm(self, key: bytes):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore
        except Exception as exc:
            raise RuntimeError("cryptography dependency is required for AES-GCM settings encryption") from exc
        return AESGCM(key)

    def _encode_b64(self, data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    def _decode_b64(self, value: str) -> bytes:
        if value is None:
            raise ValueError("base64 value must not be None")
        return base64.b64decode(value.encode("ascii"), validate=True)
