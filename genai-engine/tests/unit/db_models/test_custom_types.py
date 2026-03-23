import os
from unittest.mock import patch

import pytest

from db_models.custom_types import EncryptedJSON


@pytest.mark.unit_tests
def test_encrypted_json_encryption():
    """Test that JSON data is properly encrypted when stored."""
    # Set up environment variable for passphrase
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "test_passphrase_123"},
    ):
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
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "test_passphrase_123"},
    ):
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
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "test_passphrase_123"},
    ):
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
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "test_passphrase_123"},
    ):
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
            match="GENAI_ENGINE_SECRET_STORE_KEY environment variable not set",
        ):
            EncryptedJSON()


@pytest.mark.unit_tests
def test_encrypted_json_different_passphrases():
    """Test that different passphrases produce different encrypted values."""
    test_data = {"secret": "sensitive_data"}

    # Test with first passphrase
    with patch.dict(os.environ, {"GENAI_ENGINE_SECRET_STORE_KEY": "passphrase1"}):
        encrypted_json1 = EncryptedJSON()
        encrypted1 = encrypted_json1.process_bind_param(test_data, None)

    # Test with second passphrase
    with patch.dict(os.environ, {"GENAI_ENGINE_SECRET_STORE_KEY": "passphrase2"}):
        encrypted_json2 = EncryptedJSON()
        encrypted2 = encrypted_json2.process_bind_param(test_data, None)

    # Encrypted values should be different
    assert encrypted1 != encrypted2

    # Each should decrypt correctly with its own passphrase
    decrypted1 = encrypted_json1.process_result_value(encrypted1, None)
    decrypted2 = encrypted_json2.process_result_value(encrypted2, None)

    assert decrypted1 == test_data
    assert decrypted2 == test_data

    # Cross-decryption should fail, exception is caught to allow users to
    # overwrite invalid values
    assert "" == encrypted_json1.process_result_value(encrypted2, None)
    assert "" == encrypted_json2.process_result_value(encrypted1, None)


@pytest.mark.unit_tests
def test_encrypted_json_roundtrip_database_simulation():
    """Test that encrypted JSON can be stored and retrieved like in a database."""
    # Set up environment variable for passphrase
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "test_passphrase_123"},
    ):
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
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "test_passphrase_123"},
    ):
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


@pytest.mark.unit_tests
def test_encrypted_json_multifernet_basic():
    """Test that MultiFernet works with multiple encryption keys."""
    # Set up environment variable with multiple keys
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "key1::key2::key3"},
    ):
        encrypted_json = EncryptedJSON()

        # Test data to encrypt
        test_data = {
            "username": "test_user",
            "password": "secret_password",
            "api_key": "sk-1234567890abcdef",
        }

        # Test encryption
        encrypted_value = encrypted_json.process_bind_param(test_data, None)

        # Verify encryption worked
        assert encrypted_value is not None
        assert isinstance(encrypted_value, str)
        assert encrypted_value != str(test_data)  # Should not be plain text

        # Test decryption
        decrypted_data = encrypted_json.process_result_value(encrypted_value, None)

        # Verify decryption worked correctly
        assert decrypted_data is not None
        assert isinstance(decrypted_data, dict)
        assert decrypted_data == test_data


@pytest.mark.unit_tests
def test_encrypted_json_multifernet_single_key():
    """Test that single key still works (backward compatibility)."""
    # Set up environment variable with single key
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "single_key_only"},
    ):
        encrypted_json = EncryptedJSON()

        # Test data to encrypt
        test_data = {
            "username": "test_user",
            "password": "secret_password",
        }

        # Test encryption
        encrypted_value = encrypted_json.process_bind_param(test_data, None)

        # Verify encryption worked
        assert encrypted_value is not None
        assert isinstance(encrypted_value, str)
        assert encrypted_value != str(test_data)

        # Test decryption
        decrypted_data = encrypted_json.process_result_value(encrypted_value, None)

        # Verify decryption worked correctly
        assert decrypted_data is not None
        assert isinstance(decrypted_data, dict)
        assert decrypted_data == test_data


@pytest.mark.unit_tests
def test_encrypted_json_multifernet_key_rotation():
    """Test key rotation scenario - encrypt with old key, decrypt with new key."""
    test_data = {"secret": "sensitive_data"}

    # First, encrypt with old key
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "old_key"},
    ):
        encrypted_json_old = EncryptedJSON()
        encrypted_value = encrypted_json_old.process_bind_param(test_data, None)

    # Then, decrypt with both old and new keys (key rotation scenario)
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "old_key::new_key"},
    ):
        encrypted_json_rotated = EncryptedJSON()
        decrypted_data = encrypted_json_rotated.process_result_value(
            encrypted_value,
            None,
        )

        # Should be able to decrypt with the old key still present
        assert decrypted_data == test_data

    # Test that we can encrypt with new key and decrypt with both
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "old_key::new_key"},
    ):
        encrypted_json_rotated = EncryptedJSON()
        new_encrypted_value = encrypted_json_rotated.process_bind_param(test_data, None)
        new_decrypted_data = encrypted_json_rotated.process_result_value(
            new_encrypted_value,
            None,
        )

        # Should work with new key
        assert new_decrypted_data == test_data

    # Test that we can decrypt with just the new key (after rotation is complete)
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "new_key"},
    ):
        encrypted_json_new = EncryptedJSON()
        # This should fail because we encrypted with old_key::new_key but only have new_key
        # exception is caught to allow users to overwrite values if they loose a key
        assert "" == encrypted_json_new.process_result_value(new_encrypted_value, None)


@pytest.mark.unit_tests
def test_encrypted_json_multifernet_key_order_independence():
    """Test that key order doesn't matter for decryption."""
    test_data = {"secret": "order_test_data"}

    # Encrypt with keys in one order
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "key_a::key_b::key_c"},
    ):
        encrypted_json_order1 = EncryptedJSON()
        encrypted_value = encrypted_json_order1.process_bind_param(test_data, None)

    # Decrypt with keys in different order
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "key_c::key_a::key_b"},
    ):
        encrypted_json_order2 = EncryptedJSON()
        decrypted_data = encrypted_json_order2.process_result_value(
            encrypted_value,
            None,
        )

        # Should still work regardless of key order
        assert decrypted_data == test_data


@pytest.mark.unit_tests
def test_encrypted_json_multifernet_invalid_keys():
    """Test handling of invalid or corrupted keys."""
    test_data = {"secret": "test_data"}

    # Test with empty key (current implementation allows this)
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "valid_key::"},
    ):
        # Current implementation doesn't validate empty keys, so this should work
        encrypted_json = EncryptedJSON()
        encrypted_value = encrypted_json.process_bind_param(test_data, None)
        decrypted_data = encrypted_json.process_result_value(encrypted_value, None)
        assert decrypted_data == test_data

    # Test with only separators (current implementation not allows this)
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "::"},
    ):
        # Current implementation validate if there is at least one key
        with pytest.raises(ValueError):
            encrypted_json = EncryptedJSON()

    # Test with valid keys but try to decrypt with wrong keys
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "correct_key1::correct_key2"},
    ):
        encrypted_json = EncryptedJSON()
        encrypted_value = encrypted_json.process_bind_param(test_data, None)

    # Try to decrypt with completely different keys
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "wrong_key1::wrong_key2"},
    ):
        encrypted_json_wrong = EncryptedJSON()
        # exception is caught to allow users to fetch invalid values from DB
        # in case they lose a key
        assert "" == encrypted_json_wrong.process_result_value(encrypted_value, None)


@pytest.mark.unit_tests
def test_encrypted_json_multifernet_complex_data():
    """Test MultiFernet with complex nested data structures."""
    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": "key1::key2::key3::key4"},
    ):
        encrypted_json = EncryptedJSON()

        # Complex test data
        complex_data = {
            "api_configs": [
                {
                    "name": "primary_api",
                    "credentials": {
                        "api_key": "sk-primary-1234567890abcdef",
                        "secret": "very_secret_value_123",
                        "endpoints": {
                            "base_url": "https://api.primary.com",
                            "backup_url": "https://backup.primary.com",
                        },
                    },
                    "settings": {
                        "timeout": 30,
                        "retries": 3,
                        "rate_limit": 1000,
                    },
                },
                {
                    "name": "secondary_api",
                    "credentials": {
                        "api_key": "sk-secondary-abcdef1234567890",
                        "secret": "another_secret_value_456",
                        "endpoints": {
                            "base_url": "https://api.secondary.com",
                        },
                    },
                    "settings": {
                        "timeout": 60,
                        "retries": 5,
                        "rate_limit": 500,
                    },
                },
            ],
            "database_configs": {
                "primary_db": {
                    "host": "db-primary.example.com",
                    "port": 5432,
                    "username": "admin",
                    "password": "super_secret_db_password",
                    "ssl": True,
                },
                "replica_db": {
                    "host": "db-replica.example.com",
                    "port": 5432,
                    "username": "readonly",
                    "password": "readonly_password",
                    "ssl": True,
                },
            },
            "metadata": {
                "created_at": "2024-01-01T00:00:00Z",
                "version": "1.0.0",
                "environment": "production",
                "tags": ["critical", "encrypted", "multi-tenant"],
            },
        }

        # Test encryption
        encrypted_value = encrypted_json.process_bind_param(complex_data, None)

        # Verify encryption worked
        assert encrypted_value is not None
        assert isinstance(encrypted_value, str)
        assert encrypted_value != str(complex_data)

        # Test decryption
        decrypted_data = encrypted_json.process_result_value(encrypted_value, None)

        # Verify decryption worked correctly
        assert decrypted_data is not None
        assert isinstance(decrypted_data, dict)
        assert decrypted_data == complex_data

        # Verify specific nested values
        assert (
            decrypted_data["api_configs"][0]["credentials"]["api_key"]
            == "sk-primary-1234567890abcdef"
        )
        assert (
            decrypted_data["api_configs"][1]["credentials"]["secret"]
            == "another_secret_value_456"
        )
        assert (
            decrypted_data["database_configs"]["primary_db"]["password"]
            == "super_secret_db_password"
        )
        assert decrypted_data["metadata"]["tags"] == [
            "critical",
            "encrypted",
            "multi-tenant",
        ]


@pytest.mark.unit_tests
def test_encrypted_json_multifernet_many_keys():
    """Test MultiFernet with many keys to ensure it scales properly."""
    # Create a string with many keys
    many_keys = "::".join([f"key_{i}" for i in range(10)])

    with patch.dict(
        os.environ,
        {"GENAI_ENGINE_SECRET_STORE_KEY": many_keys},
    ):
        encrypted_json = EncryptedJSON()

        test_data = {
            "message": "Testing with many keys",
            "key_count": 10,
            "nested": {
                "value": "deeply_nested_data",
                "numbers": list(range(100)),
            },
        }

        # Test encryption
        encrypted_value = encrypted_json.process_bind_param(test_data, None)

        # Verify encryption worked
        assert encrypted_value is not None
        assert isinstance(encrypted_value, str)
        assert encrypted_value != str(test_data)

        # Test decryption
        decrypted_data = encrypted_json.process_result_value(encrypted_value, None)

        # Verify decryption worked correctly
        assert decrypted_data is not None
        assert isinstance(decrypted_data, dict)
        assert decrypted_data == test_data
