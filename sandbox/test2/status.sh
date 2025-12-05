#!/bin/bash
# Check status of all AI Red Team services

echo "================================================"
echo "AI Red Team Services Status"
echo "================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Redis
echo -e "\n${BLUE}Redis:${NC}"
if docker ps | grep -q test2-redis-1; then
    echo -e "  Status: ${GREEN}RUNNING${NC}"

    # Check Redis connectivity
    if timeout 2 docker exec test2-redis-1 redis-cli ping > /dev/null 2>&1; then
        echo -e "  Health: ${GREEN}HEALTHY${NC}"

        # Get Redis info
        REDIS_VERSION=$(docker exec test2-redis-1 redis-cli INFO server | grep redis_version | cut -d: -f2 | tr -d '\r')
        REDIS_UPTIME=$(docker exec test2-redis-1 redis-cli INFO server | grep uptime_in_seconds | cut -d: -f2 | tr -d '\r')
        echo -e "  Version: $REDIS_VERSION"
        echo -e "  Uptime: ${REDIS_UPTIME}s"

        # Get key count
        REDIS_KEYS=$(docker exec test2-redis-1 redis-cli DBSIZE | grep -o '[0-9]*')
        echo -e "  Keys: $REDIS_KEYS"
    else
        echo -e "  Health: ${RED}NOT RESPONDING${NC}"
    fi
else
    echo -e "  Status: ${RED}NOT RUNNING${NC}"
fi

# Check API Server
echo -e "\n${BLUE}API Server:${NC}"
if pgrep -f "uvicorn api.main:app" > /dev/null; then
    API_PID=$(pgrep -f "uvicorn api.main:app")
    echo -e "  Status: ${GREEN}RUNNING${NC} (PID: $API_PID)"

    # Check API health
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "  Health: ${GREEN}HEALTHY${NC}"

        # Get health response
        HEALTH=$(curl -s http://localhost:8000/health)
        echo -e "  Response: $HEALTH"
    else
        echo -e "  Health: ${RED}NOT RESPONDING${NC}"
    fi

    # Check port
    if netstat -tuln 2>/dev/null | grep -q :8000 || ss -tuln 2>/dev/null | grep -q :8000; then
        echo -e "  Port 8000: ${GREEN}LISTENING${NC}"
    else
        echo -e "  Port 8000: ${RED}NOT LISTENING${NC}"
    fi
else
    echo -e "  Status: ${RED}NOT RUNNING${NC}"
fi

# Check Database
echo -e "\n${BLUE}Database:${NC}"
if [ -f redteam.db ]; then
    DB_SIZE=$(du -h redteam.db | cut -f1)
    echo -e "  File: ${GREEN}EXISTS${NC} (redteam.db)"
    echo -e "  Size: $DB_SIZE"

    # Check if we can query it
    if python3 -c "import sqlite3; conn = sqlite3.connect('redteam.db'); cursor = conn.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"'); tables = cursor.fetchall(); print('Tables:', len(tables)); conn.close()" 2>/dev/null; then
        TABLE_COUNT=$(python3 -c "import sqlite3; conn = sqlite3.connect('redteam.db'); cursor = conn.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"'); tables = cursor.fetchall(); print(len(tables)); conn.close()" 2>/dev/null)
        echo -e "  Tables: $TABLE_COUNT"
    fi
else
    echo -e "  File: ${YELLOW}NOT FOUND${NC} (will be created on first API start)"
fi

# Docker Compose Status
echo -e "\n${BLUE}Docker Compose:${NC}"
COMPOSE_SERVICES=$(docker compose ps --services 2>/dev/null | wc -l)
COMPOSE_RUNNING=$(docker compose ps --filter "status=running" --services 2>/dev/null | wc -l)
echo -e "  Services: $COMPOSE_RUNNING/$COMPOSE_SERVICES running"

if [ $COMPOSE_RUNNING -gt 0 ]; then
    docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null
fi

# Overall Status
echo -e "\n================================================"

REDIS_OK=false
API_OK=false

docker ps | grep -q test2-redis-1 && timeout 2 docker exec test2-redis-1 redis-cli ping > /dev/null 2>&1 && REDIS_OK=true
pgrep -f "uvicorn api.main:app" > /dev/null && curl -s http://localhost:8000/health > /dev/null 2>&1 && API_OK=true

if $REDIS_OK && $API_OK; then
    echo -e "${GREEN}Overall Status: ALL SERVICES HEALTHY${NC}"
    echo ""
    echo "Run tests:"
    echo "  ./test_phase1.py  - Phase 1 foundation tests"
    echo "  ./test_phase2.py  - Phase 2 agent tests"
elif $REDIS_OK || $API_OK; then
    echo -e "${YELLOW}Overall Status: PARTIAL${NC}"
    echo ""
    echo "Start missing services:"
    echo "  ./start.sh"
else
    echo -e "${RED}Overall Status: ALL SERVICES DOWN${NC}"
    echo ""
    echo "Start services:"
    echo "  ./start.sh"
fi

echo "================================================"
