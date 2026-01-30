#!/bin/bash
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

set -euo pipefail

# Auto Migration Script
# Automatically detects and performs installation migrations
# Follows ADCL's Unix philosophy: fail fast, text-based logging

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$ROOT_DIR/logs/auto-migration-$(date +%Y%m%d_%H%M%S).log"

# Ensure logs directory exists
mkdir -p "$ROOT_DIR/logs"

log() {
    local level="$1"
    shift
    echo "[$(date -Iseconds)] [$level] $*" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_warn() {
    log "WARN" "$@"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running in Docker or host
    if [ -f /.dockerenv ]; then
        log_info "Running inside Docker container"
        DOCKER_MODE=true
    else
        log_info "Running on host system"
        DOCKER_MODE=false
        
        # Check Docker availability on host
        if ! command -v docker &> /dev/null; then
            log_error "Docker not found - required for container migrations"
            return 1
        fi
        
        if ! docker version &> /dev/null; then
            log_error "Docker daemon not available"
            return 1
        fi
    fi
    
    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found - required for migrations"
        return 1
    fi
    
    # Check for migration service
    MIGRATION_SCRIPT="$ROOT_DIR/backend/app/services/installation_migration_service.py"
    if [ ! -f "$MIGRATION_SCRIPT" ]; then
        log_error "Migration service not found: $MIGRATION_SCRIPT"
        return 1
    fi
    
    log_info "Prerequisites check passed"
    return 0
}

check_migration_needed() {
    log_info "Checking if migration is needed..."
    
    # Use Python to check migration status
    cd "$ROOT_DIR"
    
    python3 -c "
import sys
sys.path.insert(0, 'backend')
import asyncio
from app.services.installation_migration_service import InstallationMigrationService

async def main():
    service = InstallationMigrationService()
    status = await service.check_migration_needed()
    
    if status.get('migration_needed', False):
        required = status.get('required_migrations', [])
        migration_names = [m.get('name') for m in required]
        print(f'MIGRATION_NEEDED:{len(required)}:{','.join(migration_names)}')
    else:
        print('NO_MIGRATION_NEEDED')
        
    return status.get('migration_needed', False)

if __name__ == '__main__':
    try:
        result = asyncio.run(main())
        sys.exit(0 if not result else 1)
    except Exception as e:
        print(f'ERROR:{str(e)}')
        sys.exit(2)
" 2>&1
    
    return $?
}

perform_migration() {
    log_info "Performing automatic migration..."
    
    cd "$ROOT_DIR"
    
    # Create backup before migration
    BACKUP_DIR="$ROOT_DIR/backups/auto-migration-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    log_info "Creating backup: $BACKUP_DIR"
    
    # Backup critical directories
    for dir in configs agent-definitions agent-teams volumes/data; do
        if [ -d "$dir" ]; then
            log_info "Backing up: $dir"
            cp -r "$dir" "$BACKUP_DIR/" || {
                log_error "Failed to backup $dir"
                return 1
            }
        fi
    done
    
    # Backup VERSION file
    if [ -f "VERSION" ]; then
        cp "VERSION" "$BACKUP_DIR/"
    fi
    
    # Create backup manifest
    cat > "$BACKUP_DIR/manifest.json" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "script": "auto-migrate.sh",
  "backup_path": "$BACKUP_DIR",
  "pre_migration_version": "$(cat VERSION 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("version","unknown"))' 2>/dev/null || echo 'unknown')"
}
EOF
    
    log_info "Backup completed: $BACKUP_DIR"
    
    # Perform migration using Python service
    python3 -c "
import sys
sys.path.insert(0, 'backend')
import asyncio
from app.services.installation_migration_service import InstallationMigrationService

async def progress_callback(update):
    stage = update.get('stage', 'unknown')
    message = update.get('message', '')
    progress = update.get('progress', 0)
    print(f'PROGRESS:{stage}:{progress}:{message}')

async def main():
    service = InstallationMigrationService()
    
    try:
        result = await service.perform_auto_migration(progress_callback)
        
        status = result.get('status', 'unknown')
        message = result.get('message', '')
        
        if status == 'success':
            version = result.get('migrated_to_version', 'unknown')
            migrations = result.get('migrations_completed', [])
            migration_names = [m.get('migration', 'unknown') for m in migrations]
            
            print(f'SUCCESS:{version}:{len(migrations)}:{','.join(migration_names)}')
            print(f'MESSAGE:{message}')
            return 0
        else:
            error = result.get('error', 'Unknown error')
            print(f'ERROR:{status}:{error}')
            return 1
            
    except Exception as e:
        print(f'EXCEPTION:{str(e)}')
        return 2

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
" 2>&1
    
    local result=$?
    
    if [ $result -eq 0 ]; then
        log_info "Migration completed successfully"
        log_info "Backup preserved at: $BACKUP_DIR"
        return 0
    else
        log_error "Migration failed with exit code: $result"
        log_error "Backup available for rollback at: $BACKUP_DIR"
        return $result
    fi
}

rollback_migration() {
    local backup_path="$1"
    
    log_warn "Rolling back migration from backup: $backup_path"
    
    if [ ! -d "$backup_path" ]; then
        log_error "Backup directory not found: $backup_path"
        return 1
    fi
    
    cd "$ROOT_DIR"
    
    # Restore from backup
    for item in "$backup_path"/*; do
        if [ -f "$item" ] || [ -d "$item" ]; then
            basename_item=$(basename "$item")
            
            # Skip manifest.json
            if [ "$basename_item" = "manifest.json" ]; then
                continue
            fi
            
            log_info "Restoring: $basename_item"
            
            # Remove current version
            if [ -e "$basename_item" ]; then
                rm -rf "$basename_item"
            fi
            
            # Restore from backup
            cp -r "$item" "./"
        fi
    done
    
    log_info "Rollback completed"
    return 0
}

main() {
    log_info "Starting automatic installation migration"
    log_info "Log file: $LOG_FILE"
    
    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    
    # Check if migration is needed
    migration_check_output=$(check_migration_needed)
    migration_check_result=$?
    
    log_info "Migration check output: $migration_check_output"
    
    case $migration_check_result in
        0)
            log_info "No migration needed"
            echo "SUCCESS: No migration required"
            exit 0
            ;;
        1)
            log_info "Migration needed - proceeding with automatic migration"
            ;;
        2)
            log_error "Migration check failed: $migration_check_output"
            exit 1
            ;;
        *)
            log_error "Unexpected migration check result: $migration_check_result"
            exit 1
            ;;
    esac
    
    # Parse migration requirements
    if [[ $migration_check_output =~ MIGRATION_NEEDED:([0-9]+):(.+) ]]; then
        migration_count="${BASH_REMATCH[1]}"
        migration_names="${BASH_REMATCH[2]}"
        
        log_info "Found $migration_count required migrations: $migration_names"
    else
        log_error "Could not parse migration requirements"
        exit 1
    fi
    
    # Perform migration
    migration_output=$(perform_migration)
    migration_result=$?
    
    log_info "Migration output: $migration_output"
    
    if [ $migration_result -eq 0 ]; then
        log_info "Automatic migration completed successfully"
        
        # Parse success output
        if [[ $migration_output =~ SUCCESS:([^:]+):([0-9]+):(.+) ]]; then
            migrated_version="${BASH_REMATCH[1]}"
            completed_count="${BASH_REMATCH[2]}"
            completed_names="${BASH_REMATCH[3]}"
            
            log_info "Migrated to version: $migrated_version"
            log_info "Completed $completed_count migrations: $completed_names"
        fi
        
        echo "SUCCESS: Automatic migration completed successfully"
        exit 0
    else
        log_error "Migration failed with result: $migration_result"
        
        # Parse error output for rollback info
        if [[ $migration_output =~ ERROR:.*:(.+) ]]; then
            error_detail="${BASH_REMATCH[1]}"
            log_error "Migration error: $error_detail"
        fi
        
        echo "ERROR: Migration failed - check logs at $LOG_FILE"
        exit 1
    fi
}

# Handle script arguments
case "${1:-auto}" in
    "auto")
        main
        ;;
    "check")
        check_migration_needed
        result=$?
        if [ $result -eq 1 ]; then
            echo "Migration needed"
        else
            echo "No migration needed"
        fi
        exit $result
        ;;
    "rollback")
        if [ -z "${2:-}" ]; then
            echo "Usage: $0 rollback <backup_path>"
            exit 1
        fi
        rollback_migration "$2"
        ;;
    *)
        echo "Usage: $0 [auto|check|rollback <backup_path>]"
        echo "  auto     - Automatically detect and perform migration (default)"
        echo "  check    - Only check if migration is needed"
        echo "  rollback - Rollback to specified backup"
        exit 1
        ;;
esac