# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""User settings API endpoints."""

import tomllib
import tomli_w
import fcntl
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.models.settings import UserSettingsUpdate, ALLOWED_SETTINGS

router = APIRouter()


def get_settings_path() -> Path:
    """Get validated settings file path"""
    # Use container-friendly path, fallback to home
    config_dir = Path(os.getenv("ADCL_CONFIG_DIR", str(Path.home() / ".config" / "adcl")))
    config_path = config_dir / "user.conf"

    # Validate path is within expected directory
    try:
        config_path.resolve().relative_to(config_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid config path")

    return config_path


@router.get("/api/settings")
async def get_user_settings():
    """Get user settings from user.conf"""
    config_path = get_settings_path()

    # Default settings
    defaults = {
        "theme": "system",
        "log_level": "info",
        "mcp_timeout": "60",
        "auto_save": True
    }

    if not config_path.exists():
        return defaults

    try:
        with open(config_path, 'rb') as f:
            settings = tomllib.load(f)
        return {**defaults, **settings}
    except Exception as e:
        print(f"Failed to load settings: {e}")
        return defaults


@router.post("/api/settings")
async def update_user_setting(update: UserSettingsUpdate):
    """Update a single user setting with file locking"""
    config_path = get_settings_path()

    # Validate value type
    expected_type = ALLOWED_SETTINGS[update.key]
    if not isinstance(update.value, expected_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type for {update.key}. Expected {expected_type.__name__}"
        )

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Use file locking to prevent corruption from concurrent writes
        lock_path = config_path.with_suffix('.lock')
        with open(lock_path, 'w') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

            try:
                # Load existing settings
                if config_path.exists():
                    with open(config_path, 'rb') as f:
                        settings = tomllib.load(f)
                else:
                    settings = {}

                # Update the setting
                settings[update.key] = update.value

                # Atomic write: write to temp file, then rename
                temp_path = config_path.with_suffix('.tmp')
                with open(temp_path, 'wb') as f:
                    tomli_w.dump(settings, f)

                temp_path.replace(config_path)

                return {"status": "ok", "key": update.key, "value": update.value}
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}")
