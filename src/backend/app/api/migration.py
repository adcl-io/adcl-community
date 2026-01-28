# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Migration API Endpoints

Provides REST API for installation migration operations.
Follows ADCL's Tier 1 communication pattern (Frontend ↔ Backend API).
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..services.installation_migration_service import InstallationMigrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/migration", tags=["migration"])

# Global migration service instance
migration_service = InstallationMigrationService()

# Background migration state
_migration_in_progress = False
_migration_progress = {}


class MigrationStatusResponse(BaseModel):
    """Migration status response model"""
    migration_needed: bool
    current_version: str
    last_migrated: str
    required_migrations: list = []
    error: Optional[str] = None


class MigrationResponse(BaseModel):
    """Migration execution response model"""
    status: str
    message: str
    migrated_to_version: Optional[str] = None
    backup_path: Optional[str] = None
    migrations_completed: list = []
    error: Optional[str] = None


@router.get("/status", response_model=MigrationStatusResponse)
async def get_migration_status():
    """
    Check if installation migration is needed
    
    Returns:
        Migration status and required migrations
    """
    try:
        status = await migration_service.check_migration_needed()
        return MigrationStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Migration status check failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to check migration status: {str(e)}"
        )


@router.post("/auto", response_model=MigrationResponse)
async def perform_auto_migration(background_tasks: BackgroundTasks):
    """
    Perform automatic installation migration
    
    Preserves user functionality while upgrading to current version.
    Creates backup before migration and rolls back on failure.
    """
    global _migration_in_progress, _migration_progress
    
    if _migration_in_progress:
        raise HTTPException(
            status_code=409,
            detail="Migration already in progress"
        )
    
    try:
        # Check if migration is needed
        status = await migration_service.check_migration_needed()
        if not status.get("migration_needed", False):
            return MigrationResponse(
                status="success",
                message="No migration needed",
                migrated_to_version=status.get("current_version")
            )
        
        # Start migration in background
        _migration_in_progress = True
        _migration_progress = {
            "stage": "starting",
            "message": "Initializing migration...",
            "progress": 0
        }
        
        background_tasks.add_task(_run_migration_background)
        
        return MigrationResponse(
            status="started",
            message="Migration started in background. Check /api/migration/progress for updates."
        )
        
    except Exception as e:
        _migration_in_progress = False
        logger.error(f"Failed to start migration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start migration: {str(e)}"
        )


@router.get("/progress")
async def get_migration_progress():
    """
    Get current migration progress
    
    Returns:
        Current migration stage and progress
    """
    global _migration_in_progress, _migration_progress
    
    return {
        "in_progress": _migration_in_progress,
        "progress": _migration_progress
    }


@router.get("/history")
async def get_migration_history():
    """
    Get migration history
    
    Returns:
        List of previous migrations and their results
    """
    try:
        # Read migration state file for history
        migration_state_file = migration_service.migration_state_file
        if not migration_state_file.exists():
            return {"migrations": []}
        
        import json
        with open(migration_state_file, 'r') as f:
            state = json.load(f)
        
        return {
            "last_migrated_version": state.get("last_migrated_version"),
            "migration_timestamp": state.get("migration_timestamp"),
            "completed_migrations": state.get("completed_migrations", [])
        }
        
    except Exception as e:
        logger.error(f"Failed to get migration history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get migration history: {str(e)}"
        )


async def _run_migration_background():
    """Run migration in background task"""
    global _migration_in_progress, _migration_progress
    
    try:
        async def progress_callback(update):
            """Update migration progress"""
            global _migration_progress
            _migration_progress.update(update)
        
        # Perform the migration
        result = await migration_service.perform_auto_migration(progress_callback)
        
        # Update final progress
        _migration_progress.update({
            "stage": "complete",
            "message": result.get("message", "Migration completed"),
            "progress": 100,
            "final_result": result
        })
        
        logger.info(f"Background migration completed: {result.get('status')}")
        
    except Exception as e:
        logger.error(f"Background migration failed: {str(e)}")
        _migration_progress.update({
            "stage": "error",
            "message": f"Migration failed: {str(e)}",
            "progress": 0,
            "error": str(e)
        })
    
    finally:
        _migration_in_progress = False


# Startup migration check
@router.on_event("startup")
async def startup_migration_check():
    """
    Check for required migrations on startup
    
    This runs automatically when the API starts to detect
    if migration is needed after an upgrade.
    """
    try:
        logger.info("Checking for required migrations on startup...")
        
        status = await migration_service.check_migration_needed()
        if status.get("migration_needed", False):
            required = status.get("required_migrations", [])
            migration_names = [m.get("name") for m in required]
            
            logger.warning(
                f"Migration required: {len(required)} migrations needed: {migration_names}"
            )
            logger.info(
                "Use POST /api/migration/auto to perform automatic migration"
            )
        else:
            logger.info("No migration needed - installation is current")
            
    except Exception as e:
        logger.error(f"Startup migration check failed: {str(e)}")
        # Don't fail startup for migration check errors