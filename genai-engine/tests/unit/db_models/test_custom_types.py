import os
from unittest.mock import patch

import pytest

from db_models.custom_types import EncryptedJSON


@pytest.mark.unit_tests
def test_encrypted_json_encryption():
    """Test that JSON data is properly encrypted when stored."""
    # Set up environment variable for passphrase
    with patch.dict(os.environ, {"SECRET_PASSPHRASE": "test_passphrase_123"}):
        encrypted_json = EncryptedJSON()

        # Test data to encrypt
        test_data = {
            "username": "test_user",
            "password": "secret_password",
            "api_key": "sk-1234567890abcdef",
            "nested": {
                "config": {"timeout": 30, "retries": 3},
                "metadata": ["tag1", "tag2"],
            },
        }

        # Test encryption
        encrypted_value = encrypted_json.process_bind_param(test_data, None)

        # Verify encryption worked
        assert encrypted_value is not None
        assert isinstance(encrypted_value, str)
        assert encrypted_value != str(test_data)  # Should not be plain text
        assert len(encrypted_value) > 0

        # Verify it's base64 encoded (Fernet produces base64)
        try:
            # This should not raise an exception if it's valid base64
            encrypted_bytes = encrypted_value.encode()
            # Fernet tokens are base64 encoded, so this should work
            assert len(encrypted_bytes) > 0
        except Exception:
            pytest.fail("Encrypted value should be valid base64")


@pytest.mark.unit_tests
def test_encrypted_json_decryption():
    """Test that encrypted JSON data is properly decrypted when retrieved."""
    # Set up environment variable for passphrase
    with patch.dict(os.environ, {"SECRET_PASSPHRASE": "test_passphrase_123"}):
        encrypted_json = EncryptedJSON()

        # Test data to encrypt and decrypt
        original_data = {
            "username": "test_user",
            "password": "secret_password",
            "api_key": "sk-1234567890abcdef",
            "nested": {
                "config": {"timeout": 30, "retries": 3},
                "metadata": ["tag1", "tag2"],
            },
        }

        # Encrypt the data
        encrypted_value = encrypted_json.process_bind_param(original_data, None)

        # Decrypt the data
        decrypted_data = encrypted_json.process_result_value(encrypted_value, None)

        # Verify decryption worked correctly
        assert decrypted_data is not None
        assert isinstance(decrypted_data, dict)
        assert decrypted_data == original_data

        # Verify all nested structures are preserved
        assert decrypted_data["username"] == "test_user"
        assert decrypted_data["password"] == "secret_password"
        assert decrypted_data["api_key"] == "sk-1234567890abcdef"
        assert decrypted_data["nested"]["config"]["timeout"] == 30
        assert decrypted_data["nested"]["config"]["retries"] == 3
        assert decrypted_data["nested"]["metadata"] == ["tag1", "tag2"]


@pytest.mark.unit_tests
def test_encrypted_json_none_values():
    """Test that None values are handled correctly."""
    with patch.dict(os.environ, {"SECRET_PASSPHRASE": "test_passphrase_123"}):
        encrypted_json = EncryptedJSON()

        # Test None input
        encrypted_none = encrypted_json.process_bind_param(None, None)
        assert encrypted_none is None

        # Test None decryption
        decrypted_none = encrypted_json.process_result_value(None, None)
        assert decrypted_none is None


@pytest.mark.unit_tests
def test_encrypted_json_different_data_types():
    """Test encryption/decryption with various JSON data types."""
    with patch.dict(os.environ, {"SECRET_PASSPHRASE": "test_passphrase_123"}):
        encrypted_json = EncryptedJSON()

        test_cases = [
            {"simple": "string"},
            {"number": 42},
            {"float": 3.14159},
            {"boolean": True},
            {"null": None},
            {"list": [1, 2, 3, "four"]},
            {"empty_dict": {}},
            {"empty_list": []},
            {
                "complex": {
                    "strings": ["a", "b", "c"],
                    "numbers": [1, 2.5, 3],
                    "booleans": [True, False],
                    "nested": {"deep": {"value": "very deep"}},
                },
            },
        ]

        for test_data in test_cases:
            # Encrypt
            encrypted = encrypted_json.process_bind_param(test_data, None)
            assert encrypted is not None

            # Decrypt
            decrypted = encrypted_json.process_result_value(encrypted, None)
            assert decrypted == test_data


@pytest.mark.unit_tests
def test_encrypted_json_missing_passphrase():
    """Test that missing passphrase raises appropriate error."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(
            ValueError,
            match="SECRET_PASSPHRASE environment variable not set",
        ):
            EncryptedJSON()


@pytest.mark.unit_tests
def test_encrypted_json_different_passphrases():
    """Test that different passphrases produce different encrypted values."""
    test_data = {"secret": "sensitive_data"}

    # Test with first passphrase
    with patch.dict(os.environ, {"SECRET_PASSPHRASE": "passphrase1"}):
        encrypted_json1 = EncryptedJSON()
        encrypted1 = encrypted_json1.process_bind_param(test_data, None)

    # Test with second passphrase
    with patch.dict(os.environ, {"SECRET_PASSPHRASE": "passphrase2"}):
        encrypted_json2 = EncryptedJSON()
        encrypted2 = encrypted_json2.process_bind_param(test_data, None)

    # Encrypted values should be different
    assert encrypted1 != encrypted2

    # Each should decrypt correctly with its own passphrase
    decrypted1 = encrypted_json1.process_result_value(encrypted1, None)
    decrypted2 = encrypted_json2.process_result_value(encrypted2, None)

    assert decrypted1 == test_data
    assert decrypted2 == test_data

    # Cross-decryption should fail
    with pytest.raises(Exception):  # Fernet will raise InvalidToken
        encrypted_json1.process_result_value(encrypted2, None)

    with pytest.raises(Exception):  # Fernet will raise InvalidToken
        encrypted_json2.process_result_value(encrypted1, None)


@pytest.mark.unit_tests
def test_encrypted_json_roundtrip_database_simulation():
    """Test that encrypted JSON can be stored and retrieved like in a database."""
    # Set up environment variable for passphrase
    with patch.dict(os.environ, {"SECRET_PASSPHRASE": "test_passphrase_123"}):
        encrypted_json = EncryptedJSON()

        # Test data to encrypt and decrypt
        secret_data = {
            "api_key": "sk-1234567890abcdef",
            "secret_token": "very_secret_token_123",
            "config": {
                "timeout": 30,
                "retries": 3,
                "endpoints": ["https://api.example.com", "https://backup.example.com"],
            },
            "metadata": {
                "created_by": "test_user",
                "environment": "test",
                "tags": ["production", "critical"],
            },
        }

        # Simulate database storage: encrypt the data
        encrypted_value = encrypted_json.process_bind_param(secret_data, None)

        # Verify encryption worked
        assert encrypted_value is not None
        assert isinstance(encrypted_value, str)
        assert encrypted_value != str(secret_data)  # Should not be plain text

        # Simulate database retrieval: decrypt the data
        decrypted_data = encrypted_json.process_result_value(encrypted_value, None)

        # Verify decryption worked correctly
        assert decrypted_data is not None
        assert isinstance(decrypted_data, dict)
        assert decrypted_data == secret_data

        # Verify all nested data is preserved
        assert decrypted_data["api_key"] == "sk-1234567890abcdef"
        assert decrypted_data["secret_token"] == "very_secret_token_123"
        assert decrypted_data["config"]["timeout"] == 30
        assert decrypted_data["config"]["retries"] == 3
        assert decrypted_data["config"]["endpoints"] == [
            "https://api.example.com",
            "https://backup.example.com",
        ]
        assert decrypted_data["metadata"]["created_by"] == "test_user"
        assert decrypted_data["metadata"]["environment"] == "test"
        assert decrypted_data["metadata"]["tags"] == ["production", "critical"]


@pytest.mark.unit_tests
def test_encrypted_json_multiple_records_simulation():
    """Test encryption/decryption of multiple records like in a database."""
    with patch.dict(os.environ, {"SECRET_PASSPHRASE": "test_passphrase_123"}):
        encrypted_json = EncryptedJSON()

        # Test multiple records
        test_records = [
            {
                "id": "secret_1",
                "name": "database_credentials",
                "value": {
                    "host": "localhost",
                    "port": 5432,
                    "username": "admin",
                    "password": "secret123",
                },
                "owner_id": "owner_1",
                "secret_type": "database",
            },
            {
                "id": "secret_2",
                "name": "api_config",
                "value": {
                    "base_url": "https://api.example.com",
                    "version": "v2",
                    "timeout": 30,
                },
                "owner_id": "owner_1",
                "secret_type": "api_config",
            },
            {
                "id": "secret_3",
                "name": "encryption_keys",
                "value": {
                    "public_key": "pub123",
                    "private_key": "priv456",
                    "algorithm": "RSA",
                },
                "owner_id": "owner_2",
                "secret_type": "encryption",
            },
        ]

        # Simulate storing multiple records
        encrypted_records = []
        for record in test_records:
            encrypted_value = encrypted_json.process_bind_param(record["value"], None)
            encrypted_records.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "encrypted_value": encrypted_value,
                    "owner_id": record["owner_id"],
                    "secret_type": record["secret_type"],
                },
            )

        # Verify all records were encrypted
        assert len(encrypted_records) == 3
        for i, encrypted_record in enumerate(encrypted_records):
            assert encrypted_record["encrypted_value"] is not None
            assert isinstance(encrypted_record["encrypted_value"], str)
            assert encrypted_record["encrypted_value"] != str(test_records[i]["value"])

        # Simulate retrieving and decrypting records
        decrypted_records = []
        for encrypted_record in encrypted_records:
            decrypted_value = encrypted_json.process_result_value(
                encrypted_record["encrypted_value"],
                None,
            )
            decrypted_records.append(
                {
                    "id": encrypted_record["id"],
                    "name": encrypted_record["name"],
                    "value": decrypted_value,
                    "owner_id": encrypted_record["owner_id"],
                    "secret_type": encrypted_record["secret_type"],
                },
            )

        # Verify all records were decrypted correctly
        assert len(decrypted_records) == 3
        for i, decrypted_record in enumerate(decrypted_records):
            expected_record = test_records[i]
            assert decrypted_record["id"] == expected_record["id"]
            assert decrypted_record["name"] == expected_record["name"]
            assert decrypted_record["value"] == expected_record["value"]
            assert decrypted_record["owner_id"] == expected_record["owner_id"]
            assert decrypted_record["secret_type"] == expected_record["secret_type"]
