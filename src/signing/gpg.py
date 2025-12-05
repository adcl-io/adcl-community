# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
GPG Wrapper Module for Package Signing

Provides Python wrapper for GPG operations using python-gnupg library.
Implements YUM-style detached signature creation and verification.
"""

import os
import gnupg
from pathlib import Path
from typing import Tuple, Dict, Optional
from datetime import datetime


class GPGNotFoundError(Exception):
    """Raised when GPG executable is not found on the system"""
    pass


class InvalidSignatureError(Exception):
    """Raised when signature verification fails"""
    pass


class KeyNotFoundError(Exception):
    """Raised when a required key is not found in the keyring"""
    pass


def _get_gpg_instance(keyring_dir: Optional[str] = None) -> gnupg.GPG:
    """
    Get GPG instance with optional custom keyring directory.

    Args:
        keyring_dir: Optional path to custom GPG keyring directory.
                    If None, uses system default (~/.gnupg)

    Returns:
        gnupg.GPG instance

    Raises:
        GPGNotFoundError: If GPG executable is not found
    """
    try:
        if keyring_dir:
            # Ensure keyring directory exists
            Path(keyring_dir).mkdir(parents=True, exist_ok=True)
            gpg = gnupg.GPG(gnupghome=keyring_dir)
        else:
            gpg = gnupg.GPG()

        # Test if GPG is available
        gpg.list_keys()
        return gpg
    except Exception as e:
        raise GPGNotFoundError(
            f"GPG not found or not properly configured. "
            f"Please install GPG (gpg or gnupg). Error: {str(e)}"
        )


def generate_keypair(
    email: str,
    name: str,
    keyring_dir: Optional[str] = None,
    passphrase: Optional[str] = None
) -> str:
    """
    Creates new GPG keypair for package signing.

    Args:
        email: Email address for the key (used as key identifier)
        name: Full name for the key owner
        keyring_dir: Optional custom keyring directory
        passphrase: Optional passphrase to protect the key.
                   If None, reads from GPG_SIGNING_PASSPHRASE env var.
                   If env var not set, key will have no passphrase (not recommended for production)

    Returns:
        key_id: The generated key ID (fingerprint)

    Raises:
        GPGNotFoundError: If GPG is not installed
        ValueError: If key generation fails
    """
    gpg = _get_gpg_instance(keyring_dir)

    # Get passphrase from parameter or environment variable
    if passphrase is None:
        passphrase = os.getenv('GPG_SIGNING_PASSPHRASE', '')

    # Generate key with appropriate parameters
    # Using RSA 4096 for strong security
    input_data = gpg.gen_key_input(
        name_real=name,
        name_email=email,
        key_type='RSA',
        key_length=4096,
        key_usage='sign',
        expire_date=0,  # No expiration (can be changed in future)
        passphrase=passphrase
    )

    key = gpg.gen_key(input_data)

    if not key:
        raise ValueError(f"Failed to generate GPG key for {email}")

    return str(key)


def sign_file(
    filepath: str,
    key_id: str,
    keyring_dir: Optional[str] = None,
    passphrase: Optional[str] = None
) -> str:
    """
    Creates detached GPG signature for a file.

    Args:
        filepath: Path to file to sign
        key_id: GPG key ID to use for signing
        keyring_dir: Optional custom keyring directory
        passphrase: Optional passphrase for the signing key.
                   If None, reads from GPG_SIGNING_PASSPHRASE env var.
                   If env var not set, attempts to sign without passphrase.

    Returns:
        signature_path: Path to created .asc signature file

    Raises:
        GPGNotFoundError: If GPG is not installed
        KeyNotFoundError: If signing key is not found
        FileNotFoundError: If file to sign doesn't exist
        ValueError: If signing fails (including wrong passphrase)
    """
    gpg = _get_gpg_instance(keyring_dir)

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File to sign not found: {filepath}")

    # Verify key exists
    keys = gpg.list_keys(keys=key_id)
    if not keys:
        raise KeyNotFoundError(
            f"Signing key not found: {key_id}. "
            f"Available keys: {[k['keyid'] for k in gpg.list_keys()]}"
        )

    # Get passphrase from parameter or environment variable
    if passphrase is None:
        passphrase = os.getenv('GPG_SIGNING_PASSPHRASE', '')

    # Read file and create detached signature
    with open(filepath, 'rb') as f:
        signed_data = gpg.sign_file(
            f,
            keyid=key_id,
            detach=True,
            binary=False,  # ASCII-armored output
            passphrase=passphrase
        )

    if not signed_data:
        error_msg = f"Failed to sign file {filepath}"
        if signed_data.stderr:
            error_msg += f": {signed_data.stderr}"
        if "bad passphrase" in str(signed_data.stderr).lower():
            error_msg += ". Check GPG_SIGNING_PASSPHRASE environment variable."
        raise ValueError(error_msg)

    # Write signature to .asc file
    signature_path = filepath.with_suffix(filepath.suffix + '.asc')
    with open(signature_path, 'w') as f:
        f.write(str(signed_data))

    return str(signature_path)


def verify_signature(
    filepath: str,
    signature_path: str,
    keyring_dir: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Verifies a detached GPG signature against a file.

    Args:
        filepath: Path to the signed file
        signature_path: Path to the .asc signature file
        keyring_dir: Optional custom keyring directory (for user keyrings)

    Returns:
        (is_valid, error_message): Tuple of verification result and error message.
                                   error_message is empty string if valid.

    Raises:
        GPGNotFoundError: If GPG is not installed
        FileNotFoundError: If file or signature doesn't exist
    """
    gpg = _get_gpg_instance(keyring_dir)

    filepath = Path(filepath)
    signature_path = Path(signature_path)

    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if not signature_path.exists():
        raise FileNotFoundError(f"Signature file not found: {signature_path}")

    # Verify signature
    with open(signature_path, 'rb') as sig_file:
        verified = gpg.verify_file(sig_file, str(filepath))

    if verified.valid:
        return (True, "")
    else:
        # Construct detailed error message
        error_parts = []

        if verified.status == 'signature bad':
            error_parts.append("Signature does not match file content")
        elif verified.status == 'no public key':
            error_parts.append(f"Public key not found: {verified.key_id}")
            error_parts.append("Publisher may not be trusted")
        elif verified.status:
            error_parts.append(f"Verification failed: {verified.status}")

        if verified.stderr:
            error_parts.append(f"GPG error: {verified.stderr}")

        error_message = ". ".join(error_parts) if error_parts else "Signature verification failed"
        return (False, error_message)


def export_public_key(key_id: str, keyring_dir: Optional[str] = None) -> str:
    """
    Exports a public key as ASCII-armored string.

    Args:
        key_id: GPG key ID to export
        keyring_dir: Optional custom keyring directory

    Returns:
        ASCII-armored public key string

    Raises:
        GPGNotFoundError: If GPG is not installed
        KeyNotFoundError: If key is not found
    """
    gpg = _get_gpg_instance(keyring_dir)

    # Verify key exists
    keys = gpg.list_keys(keys=key_id)
    if not keys:
        raise KeyNotFoundError(
            f"Key not found: {key_id}. "
            f"Available keys: {[k['keyid'] for k in gpg.list_keys()]}"
        )

    # Export public key
    public_key = gpg.export_keys(key_id, armor=True)

    if not public_key:
        raise ValueError(f"Failed to export key {key_id}")

    return public_key


def import_public_key(key_data: str, keyring_dir: Optional[str] = None) -> str:
    """
    Imports a public key to the keyring.

    Args:
        key_data: ASCII-armored public key data
        keyring_dir: Optional custom keyring directory (typically ~/.agent-cli/keyring/)

    Returns:
        key_id: The imported key ID

    Raises:
        GPGNotFoundError: If GPG is not installed
        ValueError: If key import fails
    """
    gpg = _get_gpg_instance(keyring_dir)

    # Import key
    result = gpg.import_keys(key_data)

    if not result.count or result.count == 0:
        raise ValueError(f"Failed to import key. {result.stderr}")

    # Return the fingerprint of the first imported key
    if result.fingerprints:
        return result.fingerprints[0]
    else:
        raise ValueError("Key imported but no fingerprint returned")


def get_signature_info(signature_path: str, keyring_dir: Optional[str] = None) -> Dict:
    """
    Extracts information from a signature file.

    Args:
        signature_path: Path to .asc signature file
        keyring_dir: Optional custom keyring directory

    Returns:
        Dictionary with keys: key_id, timestamp, signer_email

    Raises:
        GPGNotFoundError: If GPG is not installed
        FileNotFoundError: If signature file doesn't exist
        ValueError: If signature cannot be parsed
    """
    gpg = _get_gpg_instance(keyring_dir)

    signature_path = Path(signature_path)
    if not signature_path.exists():
        raise FileNotFoundError(f"Signature file not found: {signature_path}")

    # Read and parse signature
    with open(signature_path, 'rb') as f:
        verified = gpg.verify_file(f)

    # Extract information
    info = {
        'key_id': verified.key_id or 'unknown',
        'timestamp': datetime.fromtimestamp(int(verified.timestamp)).isoformat() if verified.timestamp else None,
        'signer_email': verified.username or 'unknown',
        'fingerprint': verified.fingerprint or 'unknown',
        'valid': verified.valid
    }

    return info


def list_keys(keyring_dir: Optional[str] = None, secret: bool = False) -> list:
    """
    Lists all keys in the keyring.

    Args:
        keyring_dir: Optional custom keyring directory
        secret: If True, list secret (private) keys instead of public keys

    Returns:
        List of dictionaries with key information

    Raises:
        GPGNotFoundError: If GPG is not installed
    """
    gpg = _get_gpg_instance(keyring_dir)

    if secret:
        keys = gpg.list_keys(secret=True)
    else:
        keys = gpg.list_keys()

    # Format key information
    formatted_keys = []
    for key in keys:
        formatted_keys.append({
            'key_id': key['keyid'],
            'fingerprint': key['fingerprint'],
            'uids': key['uids'],
            'created': datetime.fromtimestamp(int(key['date'])).isoformat() if key.get('date') else None,
            'expires': datetime.fromtimestamp(int(key['expires'])).isoformat() if key.get('expires') and key['expires'] != '0' else None,
            'trust': key.get('trust', 'unknown')
        })

    return formatted_keys
