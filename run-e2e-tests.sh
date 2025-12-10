#!/bin/bash
# Run E2E tests inside Docker container
# No local Python installation required!

set -e

# Get script directory and source docker-compose compatibility helper
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/scripts/docker-compose-compat.sh"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== ADCL E2E Test Runner ===${NC}\n"

# Check if containers are running
if ! $DOCKER_COMPOSE ps orchestrator | grep -q "Up"; then
    echo -e "${RED}Error: orchestrator container is not running${NC}"
    echo "Start it with: $DOCKER_COMPOSE up -d"
    exit 1
fi

# Install test dependencies in container (if not already installed)
echo -e "${BLUE}Installing test dependencies in container...${NC}"
$DOCKER_COMPOSE exec -T orchestrator pip install -q httpx pytest pytest-asyncio 2>/dev/null || true

# Run the tests
echo -e "${GREEN}Running E2E tests...${NC}\n"

if [ "$1" == "--team" ]; then
    # Run with custom team
    shift
    $DOCKER_COMPOSE exec -T orchestrator python /app/tests/e2e/run_e2e_tests.py "$@"
else
    # Run all scenarios
    $DOCKER_COMPOSE exec -T orchestrator python /app/tests/e2e/run_e2e_tests.py "$@"
fi

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed!${NC}"
else
    echo -e "\n${RED}❌ Tests failed${NC}"
fi

exit $exit_code
