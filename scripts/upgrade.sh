#!/bin/bash
#
# ADCL Platform Upgrade Script
#
# Usage: ./scripts/upgrade.sh [version]
#
# Features:
# - Automatic backup before upgrade
# - Git-based version control
# - Docker container restart
# - Health check verification
# - Rollback on failure
#
# Following ADCL principles:
# - Text-based configuration
# - Fail fast with clear errors
# - Idempotent operations
# - No hidden state

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="workspace/backups"
LOG_FILE="workspace/logs/upgrade.log"
VERSION_FILE="VERSION"
DOCKER_COMPOSE_FILE="docker-compose.yml"

# Functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

error() {
    echo -e "${RED}ERROR: $*${NC}" >&2
    log "ERROR" "$*"
    exit 1
}

info() {
    echo -e "${BLUE}INFO: $*${NC}"
    log "INFO" "$*"
}

success() {
    echo -e "${GREEN}SUCCESS: $*${NC}"
    log "SUCCESS" "$*"
}

warning() {
    echo -e "${YELLOW}WARNING: $*${NC}"
    log "WARNING" "$*"
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed"
    fi

    # Check Git
    if ! command -v git &> /dev/null; then
        error "Git is not installed or not in PATH"
    fi

    # Check if in git repository
    if ! git rev-parse --git-dir &> /dev/null; then
        error "Not in a git repository"
    fi

    # Check disk space (require at least 1GB free)
    local free_space
    free_space=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "${free_space}" -lt 1 ]; then
        error "Insufficient disk space: ${free_space}GB free (need at least 1GB)"
    fi

    success "All prerequisites met"
}

# Get current version
get_current_version() {
    if [ ! -f "${VERSION_FILE}" ]; then
        echo "0.1.0"
        return
    fi

    # Extract version from VERSION file (JSON)
    grep -o '"version": *"[^"]*"' "${VERSION_FILE}" | sed 's/"version": *"\(.*\)"/\1/'
}

# Create backup
create_backup() {
    local backup_name="backup_$(date '+%Y%m%d_%H%M%S')"
    local backup_path="${BACKUP_DIR}/${backup_name}"

    info "Creating backup: ${backup_name}"

    mkdir -p "${backup_path}"

    # Backup critical files and directories
    local items=(
        "configs"
        "agent-definitions"
        "agent-teams"
        "workspace/executions"
        "${VERSION_FILE}"
        ".env"
    )

    for item in "${items[@]}"; do
        if [ -e "${item}" ]; then
            cp -r "${item}" "${backup_path}/" || warning "Failed to backup ${item}"
            info "  Backed up: ${item}"
        fi
    done

    # Create backup manifest
    cat > "${backup_path}/manifest.json" <<EOF
{
  "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "version_before": "$(get_current_version)",
  "git_commit": "$(git rev-parse HEAD)",
  "git_branch": "$(git branch --show-current)"
}
EOF

    success "Backup created: ${backup_path}"
    echo "${backup_path}"
}

# Update version file
update_version_file() {
    local new_version="$1"
    local build_number
    build_number="$(date '+%Y%m%d').001"

    info "Updating VERSION file to ${new_version}"

    # Read current VERSION file and update version
    if [ -f "${VERSION_FILE}" ]; then
        # Update version and build in JSON file
        sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"${new_version}\"/" "${VERSION_FILE}"
        sed -i "s/\"build\": \"[^\"]*\"/\"build\": \"${build_number}\"/" "${VERSION_FILE}"
        sed -i "s/\"release_date\": \"[^\"]*\"/\"release_date\": \"$(date '+%Y-%m-%d')\"/" "${VERSION_FILE}"
    fi
}

# Perform upgrade
perform_upgrade() {
    local target_version="$1"
    local current_version
    current_version=$(get_current_version)

    info "Starting upgrade from ${current_version} to ${target_version}"

    # Create backup
    local backup_path
    backup_path=$(create_backup)

    # Pull latest code
    info "Pulling latest code from git..."
    if ! git pull origin main; then
        error "Failed to pull latest code. Run 'git pull origin main' manually."
    fi

    # Checkout target version if tag exists
    if git rev-parse "v${target_version}" &> /dev/null; then
        info "Checking out version tag: v${target_version}"
        git checkout "v${target_version}"
    else
        warning "No git tag found for v${target_version}, using current HEAD"
    fi

    # Update VERSION file
    update_version_file "${target_version}"

    # Stop services
    info "Stopping services..."
    docker-compose down || warning "Failed to stop some services"

    # Pull latest images
    info "Pulling latest Docker images..."
    docker-compose pull || warning "Failed to pull some images"

    # Rebuild images
    info "Rebuilding Docker images..."
    docker-compose build --no-cache || error "Failed to rebuild images"

    # Start services
    info "Starting services..."
    docker-compose up -d || error "Failed to start services"

    # Wait for services to be healthy
    info "Waiting for services to be healthy..."
    sleep 10

    # Check health
    if ! check_health; then
        error "Health check failed after upgrade. Attempting rollback..."
        rollback "${backup_path}"
        error "Upgrade failed and rolled back to ${current_version}"
    fi

    success "Upgrade completed successfully!"
    success "Platform upgraded from ${current_version} to ${target_version}"
    success "Backup saved at: ${backup_path}"
}

# Check service health
check_health() {
    local max_retries=30
    local retry=0

    info "Checking service health..."

    while [ ${retry} -lt ${max_retries} ]; do
        if curl -sf http://localhost:8000/health &> /dev/null; then
            success "Backend is healthy"
            return 0
        fi

        retry=$((retry + 1))
        info "  Retry ${retry}/${max_retries}..."
        sleep 2
    done

    error "Health check failed after ${max_retries} attempts"
    return 1
}

# Rollback to backup
rollback() {
    local backup_path="$1"

    error "Rolling back to backup: ${backup_path}"

    # Stop services
    docker-compose down || true

    # Restore files
    if [ -d "${backup_path}" ]; then
        info "Restoring files from backup..."

        # Restore each backed up item
        for item in "${backup_path}"/*; do
            local base_item
            base_item=$(basename "${item}")

            # Skip manifest
            if [ "${base_item}" = "manifest.json" ]; then
                continue
            fi

            # Restore item
            if [ -e "${base_item}" ]; then
                rm -rf "${base_item}"
            fi
            cp -r "${item}" "./" || warning "Failed to restore ${base_item}"
            info "  Restored: ${base_item}"
        done
    else
        error "Backup path not found: ${backup_path}"
    fi

    # Restart services
    info "Restarting services..."
    docker-compose up -d || error "Failed to restart services after rollback"

    success "Rollback completed"
}

# List available backups
list_backups() {
    info "Available backups:"

    if [ ! -d "${BACKUP_DIR}" ]; then
        info "  No backups found"
        return
    fi

    for backup in "${BACKUP_DIR}"/backup_*; do
        if [ -d "${backup}" ]; then
            local manifest="${backup}/manifest.json"
            if [ -f "${manifest}" ]; then
                local version
                version=$(grep -o '"version_before": *"[^"]*"' "${manifest}" | sed 's/"version_before": *"\(.*\)"/\1/')
                local timestamp
                timestamp=$(grep -o '"timestamp": *"[^"]*"' "${manifest}" | sed 's/"timestamp": *"\(.*\)"/\1/')
                echo "  - $(basename "${backup}") (version: ${version}, time: ${timestamp})"
            else
                echo "  - $(basename "${backup}") (no manifest)"
            fi
        fi
    done
}

# Main
main() {
    # Create log directory
    mkdir -p "$(dirname "${LOG_FILE}")"

    info "ADCL Platform Upgrade Script"
    info "=============================="

    # Parse arguments
    if [ $# -eq 0 ]; then
        echo "Usage: $0 <version|--list-backups|--rollback <backup_name>>"
        echo ""
        echo "Examples:"
        echo "  $0 0.2.0              # Upgrade to version 0.2.0"
        echo "  $0 --list-backups     # List available backups"
        echo "  $0 --rollback backup_20251124_120000  # Rollback to backup"
        exit 1
    fi

    case "$1" in
        --list-backups)
            list_backups
            ;;
        --rollback)
            if [ $# -lt 2 ]; then
                error "Backup name required for rollback"
            fi
            # Validate backup name format to prevent path traversal
            if [[ ! "$2" =~ ^backup_[0-9]{8}_[0-9]{6}$ ]]; then
                error "Invalid backup name format. Expected: backup_YYYYMMDD_HHMMSS"
            fi
            rollback "${BACKUP_DIR}/$2"
            ;;
        *)
            TARGET_VERSION="$1"
            check_prerequisites
            perform_upgrade "${TARGET_VERSION}"
            ;;
    esac
}

# Run main
main "$@"
