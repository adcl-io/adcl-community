# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit Tests for GPG Wrapper Module

Tests all GPG operations including key generation, signing, verification,
and key management.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from src.signing import gpg


class TestGPGWrapper:
    """Test suite for GPG wrapper functions"""

    @pytest.fixture
    def temp_keyring(self):
        """Create temporary keyring directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def test_file(self):
        """Create temporary test file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_file.write('{"test": "data"}')
        temp_file.close()
        yield temp_file.name
        Path(temp_file.name).unlink(missing_ok=True)
        # Also clean up signature file if created
        sig_file = Path(temp_file.name + '.asc')
        sig_file.unlink(missing_ok=True)

    def test_generate_keypair(self, temp_keyring):
        """Test GPG keypair generation"""
        key_id = gpg.generate_keypair(
            email="test@example.com",
            name="Test User",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        assert key_id is not None
        assert len(key_id) > 0

        # Verify key exists in keyring
        keys = gpg.list_keys(keyring_dir=temp_keyring)
        assert len(keys) == 1
        assert keys[0]['key_id'] in key_id

    def test_generate_keypair_no_keyring(self):
        """Test keypair generation fails gracefully without GPG"""
        # This test checks error handling
        # If GPG is installed, it will succeed; if not, it should raise GPGNotFoundError
        try:
            key_id = gpg.generate_keypair(
                email="test@example.com",
                name="Test User",
                passphrase=""  # Use empty passphrase for testing
            )
            # If we get here, GPG is installed
            assert key_id is not None
        except gpg.GPGNotFoundError:
            # Expected if GPG not installed
            pass

    def test_sign_file(self, temp_keyring, test_file):
        """Test file signing with detached signature"""
        # Generate keypair first
        key_id = gpg.generate_keypair(
            email="signer@example.com",
            name="Signer",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        # Sign the file
        signature_path = gpg.sign_file(
            filepath=test_file,
            key_id=key_id,
            keyring_dir=temp_keyring,
            passphrase=""
        )

        # Verify signature file exists
        assert Path(signature_path).exists()
        assert signature_path.endswith('.asc')

        # Verify signature file contains GPG signature
        with open(signature_path, 'r') as f:
            content = f.read()
            assert '-----BEGIN PGP SIGNATURE-----' in content
            assert '-----END PGP SIGNATURE-----' in content

    def test_sign_file_missing_key(self, temp_keyring, test_file):
        """Test signing fails with non-existent key"""
        with pytest.raises(gpg.KeyNotFoundError):
            gpg.sign_file(
                filepath=test_file,
                key_id="NONEXISTENT",
                keyring_dir=temp_keyring
            )

    def test_sign_file_missing_file(self, temp_keyring):
        """Test signing fails with non-existent file"""
        # Generate keypair
        key_id = gpg.generate_keypair(
            email="test@example.com",
            name="Test",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        with pytest.raises(FileNotFoundError):
            gpg.sign_file(
                filepath="/nonexistent/file.txt",
                key_id=key_id,
                keyring_dir=temp_keyring,
                passphrase=""
            )

    def test_verify_signature_valid(self, temp_keyring, test_file):
        """Test verification of valid signature"""
        # Generate keypair and sign file
        key_id = gpg.generate_keypair(
            email="test@example.com",
            name="Test",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        signature_path = gpg.sign_file(
            filepath=test_file,
            key_id=key_id,
            keyring_dir=temp_keyring,
            passphrase=""
        )

        # Verify signature
        is_valid, error_msg = gpg.verify_signature(
            filepath=test_file,
            signature_path=signature_path,
            keyring_dir=temp_keyring
        )

        assert is_valid is True
        assert error_msg == ""

    def test_verify_signature_invalid(self, temp_keyring, test_file):
        """Test verification fails for tampered file"""
        # Generate keypair and sign file
        key_id = gpg.generate_keypair(
            email="test@example.com",
            name="Test",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        signature_path = gpg.sign_file(
            filepath=test_file,
            key_id=key_id,
            keyring_dir=temp_keyring,
            passphrase=""
        )

        # Tamper with the file
        with open(test_file, 'w') as f:
            f.write('{"tampered": "data"}')

        # Verify signature should fail
        is_valid, error_msg = gpg.verify_signature(
            filepath=test_file,
            signature_path=signature_path,
            keyring_dir=temp_keyring
        )

        assert is_valid is False
        assert len(error_msg) > 0

    def test_verify_signature_missing_key(self, temp_keyring, test_file):
        """Test verification fails when public key is not in keyring"""
        # Generate keypair in one keyring
        keyring1 = tempfile.mkdtemp()
        try:
            key_id = gpg.generate_keypair(
                email="test@example.com",
                name="Test",
                keyring_dir=keyring1,
                passphrase=""  # Use empty passphrase for testing
            )

            signature_path = gpg.sign_file(
                filepath=test_file,
                key_id=key_id,
                keyring_dir=keyring1,
                passphrase=""
            )

            # Try to verify with different keyring (missing key)
            is_valid, error_msg = gpg.verify_signature(
                filepath=test_file,
                signature_path=signature_path,
                keyring_dir=temp_keyring
            )

            assert is_valid is False
            assert "Public key not found" in error_msg or "no public key" in error_msg.lower()
        finally:
            shutil.rmtree(keyring1)

    def test_export_public_key(self, temp_keyring):
        """Test exporting public key"""
        # Generate keypair
        key_id = gpg.generate_keypair(
            email="test@example.com",
            name="Test User",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        # Export public key
        public_key = gpg.export_public_key(key_id, keyring_dir=temp_keyring)

        assert public_key is not None
        assert '-----BEGIN PGP PUBLIC KEY BLOCK-----' in public_key
        assert '-----END PGP PUBLIC KEY BLOCK-----' in public_key

    def test_export_public_key_missing(self, temp_keyring):
        """Test exporting non-existent key fails"""
        with pytest.raises(gpg.KeyNotFoundError):
            gpg.export_public_key("NONEXISTENT", keyring_dir=temp_keyring)

    def test_import_export_roundtrip(self, temp_keyring):
        """Test importing and exporting keys roundtrip"""
        # Generate keypair in one keyring
        key_id = gpg.generate_keypair(
            email="test@example.com",
            name="Test User",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        # Export public key
        public_key = gpg.export_public_key(key_id, keyring_dir=temp_keyring)

        # Import to new keyring
        new_keyring = tempfile.mkdtemp()
        try:
            imported_key_id = gpg.import_public_key(public_key, keyring_dir=new_keyring)

            assert imported_key_id is not None
            assert len(imported_key_id) > 0

            # Verify key exists in new keyring
            keys = gpg.list_keys(keyring_dir=new_keyring)
            assert len(keys) == 1
        finally:
            shutil.rmtree(new_keyring)

    def test_import_public_key_invalid(self, temp_keyring):
        """Test importing invalid key data fails"""
        with pytest.raises(ValueError):
            gpg.import_public_key("invalid key data", keyring_dir=temp_keyring)

    def test_get_signature_info(self, temp_keyring, test_file):
        """Test extracting signature information"""
        # Generate keypair and sign file
        key_id = gpg.generate_keypair(
            email="signer@example.com",
            name="Test Signer",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        signature_path = gpg.sign_file(
            filepath=test_file,
            key_id=key_id,
            keyring_dir=temp_keyring,
            passphrase=""
        )

        # Get signature info
        info = gpg.get_signature_info(signature_path, keyring_dir=temp_keyring)

        assert 'key_id' in info
        assert 'timestamp' in info
        assert 'signer_email' in info
        assert 'fingerprint' in info
        assert 'valid' in info

        # Verify some fields are populated
        assert info['key_id'] is not None
        assert info['valid'] is True

    def test_get_signature_info_missing_file(self, temp_keyring):
        """Test getting signature info fails for non-existent file"""
        with pytest.raises(FileNotFoundError):
            gpg.get_signature_info("/nonexistent/signature.asc", keyring_dir=temp_keyring)

    def test_list_keys_empty(self, temp_keyring):
        """Test listing keys in empty keyring"""
        keys = gpg.list_keys(keyring_dir=temp_keyring)
        assert keys == []

    def test_list_keys_with_keys(self, temp_keyring):
        """Test listing keys after generating some"""
        # Generate multiple keypairs
        key_id1 = gpg.generate_keypair(
            email="user1@example.com",
            name="User 1",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        key_id2 = gpg.generate_keypair(
            email="user2@example.com",
            name="User 2",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        # List keys
        keys = gpg.list_keys(keyring_dir=temp_keyring)

        assert len(keys) == 2
        key_ids = [k['key_id'] for k in keys]
        assert any(key_id1 in kid for kid in key_ids)
        assert any(key_id2 in kid for kid in key_ids)

        # Verify key structure
        for key in keys:
            assert 'key_id' in key
            assert 'fingerprint' in key
            assert 'uids' in key
            assert 'created' in key

    def test_list_secret_keys(self, temp_keyring):
        """Test listing secret (private) keys"""
        # Generate keypair
        key_id = gpg.generate_keypair(
            email="test@example.com",
            name="Test User",
            keyring_dir=temp_keyring,
            passphrase=""  # Use empty passphrase for testing
        )

        # List secret keys
        secret_keys = gpg.list_keys(keyring_dir=temp_keyring, secret=True)

        assert len(secret_keys) == 1
        assert secret_keys[0]['key_id'] in key_id

    def test_signature_verification_workflow(self, temp_keyring, test_file):
        """
        Integration test: Full workflow from key generation to verification.

        Simulates publisher signing and user verifying.
        """
        # Publisher workflow
        publisher_keyring = temp_keyring
        user_keyring = tempfile.mkdtemp()

        try:
            # 1. Publisher generates keypair
            publisher_key_id = gpg.generate_keypair(
                email="publisher@example.com",
                name="Publisher",
                keyring_dir=publisher_keyring,
                passphrase=""  # Use empty passphrase for testing
            )

            # 2. Publisher signs package
            signature_path = gpg.sign_file(
                filepath=test_file,
                key_id=publisher_key_id,
                keyring_dir=publisher_keyring,
                passphrase=""
            )

            # 3. Publisher exports public key
            public_key = gpg.export_public_key(
                publisher_key_id,
                keyring_dir=publisher_keyring
            )

            # 4. User imports publisher's public key
            imported_key_id = gpg.import_public_key(
                public_key,
                keyring_dir=user_keyring
            )

            # 5. User verifies package signature
            is_valid, error_msg = gpg.verify_signature(
                filepath=test_file,
                signature_path=signature_path,
                keyring_dir=user_keyring
            )

            # Verification should succeed
            assert is_valid is True
            assert error_msg == ""

            # 6. Tamper with file and verify again
            with open(test_file, 'w') as f:
                f.write('{"tampered": "data"}')

            is_valid, error_msg = gpg.verify_signature(
                filepath=test_file,
                signature_path=signature_path,
                keyring_dir=user_keyring
            )

            # Verification should fail
            assert is_valid is False
            assert len(error_msg) > 0

        finally:
            shutil.rmtree(user_keyring)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
