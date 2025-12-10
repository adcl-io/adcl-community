#!/bin/bash
# Docker Compose Compatibility Helper
# Detects and sets the correct docker compose command for different Docker versions
#
# Usage: source scripts/docker-compose-compat.sh
# Then use: $DOCKER_COMPOSE instead of docker-compose

# Detect which docker compose command is available
if command -v docker-compose &> /dev/null; then
    # Older Docker with separate docker-compose binary
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    # Newer Docker with compose plugin
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ Error: Neither 'docker-compose' nor 'docker compose' is available"
    echo "   Please install Docker Compose:"
    echo "   - Docker Compose V2 (plugin): https://docs.docker.com/compose/install/"
    echo "   - Docker Compose V1 (standalone): https://docs.docker.com/compose/install/standalone/"
    exit 1
fi

# Export for use in scripts
export DOCKER_COMPOSE
