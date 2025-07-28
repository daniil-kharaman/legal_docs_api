"""
Token encryption utilities using Fernet symmetric encryption.
"""
import os
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

class EncryptionError(Exception):
    pass


class TokenEncryption:
    """Handles encryption/decryption of sensitive token data using Fernet."""


    def __init__(self):
        self._key = self._get_key()
        self._fernet = Fernet(self._key)


    def _get_key(self) -> bytes:
        """Get encryption key from environment or generate new one."""
        key_str = os.getenv('TOKEN_ENCRYPTION_KEY')
        
        if not key_str:
            raise EncryptionError('Encryption key was not found.')
        return key_str.encode()


    def encrypt(self, data: str) -> str:
        """Encrypt token data."""
        try:
            encrypted_data = self._fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            raise EncryptionError(f"Failed to encrypt token data: {e}")

    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt token data."""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            raise EncryptionError(f"Failed to decrypt token data: {e}")
