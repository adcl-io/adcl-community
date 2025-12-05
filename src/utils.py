# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Utility functions for GPG package signing system
"""

import os
from pathlib import Path
from typing import Optional


def load_env_file(env_path: Optional[str] = None) -> None:
    """
    Load environment variables from .env file.

    Args:
        env_path: Path to .env file. If None, looks for .env in current directory
                 and parent directories.
    """
    if env_path:
        env_file = Path(env_path)
    else:
        # Search for .env file in current and parent directories
        current = Path.cwd()
        env_file = None

        for _ in range(5):  # Search up to 5 levels up
            candidate = current / '.env'
            if candidate.exists():
                env_file = candidate
                break
            current = current.parent

    if not env_file or not env_file.exists():
        return  # No .env file found, that's okay

    # Parse and load .env file
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # Set environment variable if not already set
                if key and not os.getenv(key):
                    os.environ[key] = value


def get_gpg_passphrase() -> str:
    """
    Get GPG signing passphrase from environment.

    Returns:
        Passphrase string (may be empty if not set)
    """
    return os.getenv('GPG_SIGNING_PASSPHRASE', '')


def set_gpg_passphrase(passphrase: str) -> None:
    """
    Set GPG signing passphrase in environment.

    Args:
        passphrase: The passphrase to set
    """
    os.environ['GPG_SIGNING_PASSPHRASE'] = passphrase
