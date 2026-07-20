"""
Rinox Sentinel - Encryption Utility
Encrypt/decrypt sensitive data (API keys) using Fernet
"""

import os
import base64
import logging
from typing import Optional

logger = logging.getLogger("Rinox.Encryption")


class Encryption:
    """Encrypt and decrypt sensitive configuration data"""

    def __init__(self, key: Optional[str] = None):
        self.key = key or os.getenv("ENCRYPTION_KEY", "")
        self._fernet = None

    def _get_fernet(self):
        if self._fernet is None:
            try:
                from cryptography.fernet import Fernet
                if len(self.key) < 32:
                    key_bytes = self.key.encode().ljust(32, b'\0')[:32]
                    self.key = base64.urlsafe_b64encode(key_bytes).decode()
                elif not self.key.endswith("="):
                    key_bytes = self.key.encode().ljust(32, b'\0')[:32]
                    self.key = base64.urlsafe_b64encode(key_bytes).decode()
                self._fernet = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)
            except Exception as e:
                logger.warning(f"Encryption init failed (using plaintext): {e}")
        return self._fernet

    def encrypt(self, data: str) -> str:
        """Encrypt a string"""
        f = self._get_fernet()
        if f:
            try:
                return f.encrypt(data.encode()).decode()
            except Exception as e:
                logger.warning(f"Encryption failed: {e}")
        return data

    def decrypt(self, data: str) -> str:
        """Decrypt a string"""
        f = self._get_fernet()
        if f:
            try:
                return f.decrypt(data.encode()).decode()
            except Exception as e:
                logger.warning(f"Decryption failed: {e}")
        return data