import pytest
import os
from unittest.mock import patch, Mock
from cryptography.fernet import Fernet

from auth.token_encryption import TokenEncryption, EncryptionError


class TestTokenEncryption:
    """Tests for the TokenEncryption class"""

    @pytest.fixture
    def valid_key(self):
        """Generate a valid Fernet key for testing"""
        return Fernet.generate_key().decode()

    @pytest.fixture
    def encryption_instance(self, valid_key):
        """Create a TokenEncryption instance with mocked environment"""
        with patch.dict(os.environ, {'TOKEN_ENCRYPTION_KEY': valid_key}):
            return TokenEncryption()

    def test_init_with_valid_key(self, valid_key):
        """Test initialization with valid encryption key"""
        with patch.dict(os.environ, {'TOKEN_ENCRYPTION_KEY': valid_key}):
            encryptor = TokenEncryption()
            assert encryptor._key == valid_key.encode()
            assert encryptor._fernet is not None

    def test_init_without_key_raises_error(self):
        """Test initialization fails when encryption key is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EncryptionError, match='Encryption key was not found'):
                TokenEncryption()

    def test_encrypt_returns_string(self, encryption_instance):
        """Test encrypt method returns a string"""
        data = "test_token_data"
        encrypted = encryption_instance.encrypt(data)

        assert isinstance(encrypted, str)
        assert encrypted != data
        assert len(encrypted) > 0

    def test_decrypt_returns_original_data(self, encryption_instance):
        """Test decrypt returns the original data"""
        original_data = "sensitive_token_12345"
        encrypted = encryption_instance.encrypt(original_data)
        decrypted = encryption_instance.decrypt(encrypted)

        assert decrypted == original_data

    def test_encrypt_decrypt_roundtrip(self, encryption_instance):
        """Test full encryption and decryption cycle"""
        test_cases = [
            "simple_string",
            "complex@string#with$special%chars!",
            "1234567890",
            '{"access_token": "abc123", "refresh_token": "xyz789"}',
            "Unicode: 你好世界 🔐"
        ]

        for data in test_cases:
            encrypted = encryption_instance.encrypt(data)
            decrypted = encryption_instance.decrypt(encrypted)
            assert decrypted == data

    def test_encrypt_same_data_produces_different_ciphertext(self, encryption_instance):
        """Test that encrypting the same data twice produces different results"""
        data = "test_data"
        encrypted1 = encryption_instance.encrypt(data)
        encrypted2 = encryption_instance.encrypt(data)

        # Ciphertexts should be different due to random IV
        assert encrypted1 != encrypted2
        # But both should decrypt to the same value
        assert encryption_instance.decrypt(encrypted1) == data
        assert encryption_instance.decrypt(encrypted2) == data

    def test_decrypt_invalid_data_raises_error(self, encryption_instance):
        """Test decrypt fails with invalid encrypted data"""
        invalid_data = "this_is_not_encrypted_data"

        with pytest.raises(EncryptionError, match='Failed to decrypt token data'):
            encryption_instance.decrypt(invalid_data)

    def test_decrypt_corrupted_data_raises_error(self, encryption_instance):
        """Test decrypt fails with corrupted data"""
        data = "test_data"
        encrypted = encryption_instance.encrypt(data)

        # Corrupt the encrypted data
        corrupted = encrypted[:-5] + "xxxxx"

        with pytest.raises(EncryptionError, match='Failed to decrypt token data'):
            encryption_instance.decrypt(corrupted)

    def test_decrypt_with_wrong_key_raises_error(self, encryption_instance):
        """Test decrypt fails when using a different key"""
        data = "test_data"
        encrypted = encryption_instance.encrypt(data)

        # Create new instance with different key
        new_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {'TOKEN_ENCRYPTION_KEY': new_key}):
            new_encryptor = TokenEncryption()

            with pytest.raises(EncryptionError, match='Failed to decrypt token data'):
                new_encryptor.decrypt(encrypted)

    def test_encrypt_empty_string(self, encryption_instance):
        """Test encrypting an empty string"""
        data = ""
        encrypted = encryption_instance.encrypt(data)
        decrypted = encryption_instance.decrypt(encrypted)

        assert decrypted == data

    def test_encrypt_large_data(self, encryption_instance):
        """Test encrypting large data"""
        # Create a large JSON-like token
        data = '{"token": "' + 'a' * 10000 + '"}'
        encrypted = encryption_instance.encrypt(data)
        decrypted = encryption_instance.decrypt(encrypted)

        assert decrypted == data

    @patch.object(Fernet, 'encrypt')
    def test_encrypt_exception_handling(self, mock_encrypt, encryption_instance):
        """Test encrypt handles unexpected exceptions"""
        mock_encrypt.side_effect = Exception("Encryption failed")

        with pytest.raises(EncryptionError, match='Failed to encrypt token data'):
            encryption_instance.encrypt("test")

    @patch.object(Fernet, 'decrypt')
    def test_decrypt_exception_handling(self, mock_decrypt, encryption_instance):
        """Test decrypt handles unexpected exceptions"""
        mock_decrypt.side_effect = Exception("Decryption failed")

        with pytest.raises(EncryptionError, match='Failed to decrypt token data'):
            encryption_instance.decrypt("test")
